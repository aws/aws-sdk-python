# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from smithy_aws_core.config import AwsConfigOverrides
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import (
    AWSCredentialsIdentity,
    AWSCredentialsResolver,
    AWSIdentityProperties,
    StaticCredentialsResolver,
)
from smithy_aws_core.identity.chain import StandardProvider
from smithy_aws_core.identity.chain.provider import ChainIdentityProvider, ChainSetup
from smithy_core.interfaces.identity import IdentityResolver
from smithy_http.interfaces import HTTPClient

from ._assume_role import (
    DEFAULT_STS_REGION,
    AssumeRoleConfigurationError,
    AssumeRolePlan,
    CredentialSource,
    StaticSource,
    assume_role_input,
    default_session_name,
    find_provider,
    first_resolver,
    identity_from_response,
    plan_profile,
    require_provider,
    resolve_sts_region,
    validate_profile,
)

if TYPE_CHECKING:
    from aws_sdk_sts.client import STSClient

__all__ = (
    "AssumeRoleConfigurationError",
    "AssumeRoleCredentialsResolver",
    "ProfileAssumeRoleCredentialsResolver",
)

_CHAIN_PROVIDER_ENTRY_POINT_GROUP = "smithy_aws_core.identity.chain_providers"


class AssumeRoleCredentialsResolver(
    IdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves credentials with an STS AssumeRole call."""

    def __init__(
        self,
        *,
        source_resolver: AWSCredentialsResolver,
        role_arn: str,
        role_session_name: str | None = None,
        external_id: str | None = None,
        duration_seconds: int | None = None,
        region: str | None = None,
        http_client: HTTPClient | None = None,
    ) -> None:
        self._source_resolver = source_resolver
        self._role_arn = role_arn
        self._role_session_name = role_session_name or default_session_name()
        self._external_id = external_id
        self._duration_seconds = duration_seconds
        self._region = region or DEFAULT_STS_REGION
        self._http_client = http_client
        self._credentials: AWSCredentialsIdentity | None = None
        self._client: STSClient | None = None
        self._refresh_lock = threading.Lock()

    def get_identity(
        self,
        *,
        properties: AWSIdentityProperties,
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise call STS AssumeRole."""
        if self._credentials is not None and not self._credentials.is_expired:
            return self._credentials

        with self._refresh_lock:
            if self._credentials is not None and not self._credentials.is_expired:
                return self._credentials
            self._credentials = self._assume_role()
            return self._credentials

    def _assume_role(self) -> AWSCredentialsIdentity:
        from aws_sdk_sts.client import STSClient
        from aws_sdk_sts.config import STSConfig

        overrides: AwsConfigOverrides = {
            "aws_credentials_identity_resolver": self._source_resolver,
            "region": self._region,
        }
        if self._client is None and self._http_client is not None:
            # CAUTION: never closed, since closing it would close the caller's transport.
            overrides["transport"] = self._http_client
            self._client = STSClient(config=STSConfig.resolve(**overrides))
        if self._client is not None:
            return self._call(self._client)
        with STSClient(config=STSConfig.resolve(**overrides)) as client:
            return self._call(client)

    def _call(self, client: STSClient) -> AWSCredentialsIdentity:
        response = client.assume_role(
            assume_role_input(
                role_arn=self._role_arn,
                role_session_name=self._role_session_name,
                external_id=self._external_id,
                duration_seconds=self._duration_seconds,
            )
        )
        return identity_from_response(response)


class ProfileAssumeRoleCredentialsResolver(
    IdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves credentials from a profile-based AssumeRole configuration."""

    def __init__(
        self,
        *,
        profile_name: str,
        config_file: MergedConfig,
        region_override: str | None = None,
        http_client: HTTPClient | None = None,
    ) -> None:
        validate_profile(config_file, profile_name)
        self._profile_name = profile_name
        self._config_file = config_file
        self._region = region_override or resolve_sts_region(
            config_file=config_file, profile_name=profile_name
        )
        self._http_client = http_client
        self._delegate: AssumeRoleCredentialsResolver | None = None
        self._setup_lock = threading.Lock()

    def get_identity(
        self,
        *,
        properties: AWSIdentityProperties,
    ) -> AWSCredentialsIdentity:
        """Create delegate resolver if needed, then fetch assume role credentials."""
        if self._delegate is None:
            with self._setup_lock:
                if self._delegate is None:
                    self._delegate = self._create_delegate()
        return self._delegate.get_identity(properties=properties)

    def _create_delegate(self) -> AssumeRoleCredentialsResolver:
        return self._build_assume_role(
            plan_profile(self._config_file, self._profile_name)
        )

    def _find_provider(self, slot: StandardProvider) -> ChainIdentityProvider | None:
        return find_provider(_CHAIN_PROVIDER_ENTRY_POINT_GROUP, slot)

    def _build_assume_role(self, plan: AssumeRolePlan) -> AssumeRoleCredentialsResolver:
        return AssumeRoleCredentialsResolver(
            source_resolver=self._build_source(plan.source),
            role_arn=plan.role_arn,
            role_session_name=plan.role_session_name,
            external_id=plan.external_id,
            duration_seconds=plan.duration_seconds,
            region=self._region,
            http_client=self._http_client,
        )

    def _build_source(
        self, source: StaticSource | CredentialSource | AssumeRolePlan
    ) -> AWSCredentialsResolver:
        match source:
            case StaticSource(identity=identity):
                return StaticCredentialsResolver(identity)
            case CredentialSource():
                provider = require_provider(self._find_provider(source.slot), source)
                setup = ChainSetup(
                    region_override=self._region, http_client=self._http_client
                )
                setup.set_current_provider(provider)
                provider.setup(AWSCredentialsIdentity, setup)
                return first_resolver(setup.resolvers, source)
            case AssumeRolePlan():
                return self._build_assume_role(source)
