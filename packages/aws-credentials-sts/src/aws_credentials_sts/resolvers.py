# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Callable
from importlib import metadata
from typing import TYPE_CHECKING, cast

from smithy_aws_core.config import AwsConfigOverrides
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import (
    AWSCredentialsIdentity,
    AWSCredentialsResolver,
    AWSIdentityProperties,
    StaticCredentialsResolver,
)
from smithy_aws_core.identity.chain import (
    ChainIdentityProvider,
    ChainSetup,
    StandardProvider,
)
from smithy_core.aio.interfaces.identity import IdentityResolver
from smithy_core.exceptions import SmithyError, SmithyIdentityError
from smithy_http.aio.interfaces import HTTPClient

if TYPE_CHECKING:
    from aws_sdk_sts.client import AsyncSTSClient

_CHAIN_PROVIDER_ENTRY_POINT_GROUP = "smithy_aws_core.identity.chain_providers"
_DEFAULT_STS_REGION = "us-east-1"

_ACCESS_KEY_ID = "aws_access_key_id"
_SECRET_ACCESS_KEY = "aws_secret_access_key"  # noqa: S105
_SESSION_TOKEN = "aws_session_token"  # noqa: S105
_ACCOUNT_ID = "aws_account_id"
_ROLE_ARN = "role_arn"
_ROLE_SESSION_NAME = "role_session_name"
_EXTERNAL_ID = "external_id"
_DURATION_SECONDS = "duration_seconds"
_SOURCE_PROFILE = "source_profile"
_CREDENTIAL_SOURCE = "credential_source"
_REGION = "region"

_CREDENTIAL_SOURCE_SLOTS = {
    "Environment": StandardProvider.ENVIRONMENT,
    "EcsContainer": StandardProvider.ECS_CONTAINER,
    "Ec2InstanceMetadata": StandardProvider.EC2_INSTANCE_METADATA,
}


class AssumeRoleConfigurationError(SmithyError):
    """Raised when AssumeRole credential configuration is invalid."""


def _account_id_from_arn(arn: str | None) -> str | None:
    if arn is None:
        return None
    parts = arn.split(":")
    return parts[4] if len(parts) >= 5 and parts[4] else None


def _resolve_sts_region(
    *,
    config_file: MergedConfig | None = None,
    profile_name: str | None = None,
) -> str:
    profile_region = (
        config_file.get(profile_name, _REGION)
        if config_file is not None and profile_name is not None
        else None
    )
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or profile_region
        or _DEFAULT_STS_REGION
    )


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
        self._role_session_name = (
            role_session_name or f"aws-sdk-python-{uuid.uuid4().hex[:16]}"
        )
        self._external_id = external_id
        self._duration_seconds = duration_seconds
        self._region = region or _DEFAULT_STS_REGION
        self._http_client = http_client
        self._credentials: AWSCredentialsIdentity | None = None
        self._client: AsyncSTSClient | None = None
        self._refresh_lock = asyncio.Lock()

    async def get_identity(
        self,
        *,
        properties: AWSIdentityProperties,
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise call STS AssumeRole."""
        if self._credentials is not None and not self._credentials.is_expired:
            return self._credentials

        async with self._refresh_lock:
            if self._credentials is not None and not self._credentials.is_expired:
                return self._credentials
            self._credentials = await self._assume_role()
            return self._credentials

    async def _assume_role(self) -> AWSCredentialsIdentity:
        from aws_sdk_sts.client import AsyncSTSClient
        from aws_sdk_sts.config import AsyncSTSConfig

        if self._client is None:
            overrides: AwsConfigOverrides = {
                "aws_credentials_identity_resolver": self._source_resolver,
                "region": self._region,
            }
            if self._http_client is not None:
                overrides["transport"] = self._http_client
            self._client = AsyncSTSClient(
                config=await AsyncSTSConfig.resolve(**overrides)
            )

        response = await self._client.assume_role(
            role_arn=self._role_arn,
            role_session_name=self._role_session_name,
            external_id=self._external_id,
            duration_seconds=self._duration_seconds,
        )

        credentials = response.credentials
        if credentials is None:
            raise SmithyIdentityError(
                "STS AssumeRole response did not contain credentials."
            )

        assumed_role_arn = (
            response.assumed_role_user.arn
            if response.assumed_role_user is not None
            else None
        )
        return AWSCredentialsIdentity(
            access_key_id=credentials.access_key_id,
            secret_access_key=credentials.secret_access_key,
            session_token=credentials.session_token,
            expiration=credentials.expiration,
            account_id=_account_id_from_arn(assumed_role_arn),
        )


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
        if config_file.get_profile(profile_name) is None:
            raise AssumeRoleConfigurationError(
                f"Profile '{profile_name}' does not exist."
            )
        self._profile_name = profile_name
        self._config_file = config_file
        self._region = region_override or _resolve_sts_region(
            config_file=config_file, profile_name=profile_name
        )
        self._http_client = http_client
        self._delegate: AssumeRoleCredentialsResolver | None = None
        self._setup_lock = asyncio.Lock()

    async def get_identity(
        self,
        *,
        properties: AWSIdentityProperties,
    ) -> AWSCredentialsIdentity:
        """Create delegate resolver if needed, then fetch assume role credentials."""
        if self._delegate is None:
            async with self._setup_lock:
                if self._delegate is None:
                    self._delegate = await self._create_assume_role_resolver(
                        profile_name=self._profile_name,
                        visited=(self._profile_name,),
                    )
        return await self._delegate.get_identity(properties=properties)

    async def _create_assume_role_resolver(
        self,
        *,
        profile_name: str,
        visited: tuple[str, ...],
    ) -> AssumeRoleCredentialsResolver:
        config_file = self._config_file
        role_arn = config_file.get(profile_name, _ROLE_ARN)
        if role_arn is None:
            raise AssumeRoleConfigurationError(
                f"Profile '{profile_name}' does not define role_arn."
            )

        source_profile = config_file.get(profile_name, _SOURCE_PROFILE)
        credential_source = config_file.get(profile_name, _CREDENTIAL_SOURCE)
        if source_profile is not None and credential_source is not None:
            raise AssumeRoleConfigurationError(
                f"Profile '{profile_name}' cannot define both 'source_profile' and 'credential_source'."
            )
        elif source_profile is not None:
            source_resolver = await self._create_resolver_from_source_profile(
                source_profile,
                visited,
            )
        elif credential_source is not None:
            source_resolver = await self._create_resolver_from_credential_source(
                credential_source,
                self._region,
            )
        else:
            raise AssumeRoleConfigurationError(
                f"Profile '{profile_name}' must define either 'source_profile' or 'credential_source'."
            )

        return AssumeRoleCredentialsResolver(
            source_resolver=source_resolver,
            role_arn=role_arn,
            role_session_name=config_file.get(profile_name, _ROLE_SESSION_NAME),
            external_id=config_file.get(profile_name, _EXTERNAL_ID),
            duration_seconds=self._parse_duration_seconds(profile_name),
            region=self._region,
            http_client=self._http_client,
        )

    async def _create_resolver_from_source_profile(
        self,
        source_profile_name: str,
        visited: tuple[str, ...],
    ) -> AWSCredentialsResolver:
        config_file = self._config_file
        is_direct_self_reference = (
            len(visited) > 0 and source_profile_name == visited[-1]
        )
        if source_profile_name in visited and not is_direct_self_reference:
            path = " -> ".join((*visited, source_profile_name))
            raise AssumeRoleConfigurationError(
                f"Circular source_profile reference: {path}."
            )

        if config_file.get_profile(source_profile_name) is None:
            raise AssumeRoleConfigurationError(
                f"Source profile '{source_profile_name}' does not exist."
            )

        if any(
            config_file.get(source_profile_name, key) is not None
            for key in (_ACCESS_KEY_ID, _SECRET_ACCESS_KEY, _SESSION_TOKEN)
        ):
            return self._create_static_resolver(source_profile_name)

        if is_direct_self_reference:
            raise AssumeRoleConfigurationError(
                f"Self-referencing profile '{source_profile_name}' must contain "
                "complete static credentials."
            )

        if config_file.get(source_profile_name, _ROLE_ARN) is not None:
            return await self._create_assume_role_resolver(
                profile_name=source_profile_name,
                visited=(*visited, source_profile_name),
            )

        raise AssumeRoleConfigurationError(
            f"Source profile '{source_profile_name}' has no supported credential source."
        )

    def _create_static_resolver(
        self,
        profile_name: str,
    ) -> AWSCredentialsResolver:
        config_file = self._config_file
        access_key_id = config_file.get(profile_name, _ACCESS_KEY_ID)
        secret_access_key = config_file.get(profile_name, _SECRET_ACCESS_KEY)
        if access_key_id is None or secret_access_key is None:
            raise AssumeRoleConfigurationError(
                f"Profile '{profile_name}' contains partial credentials."
            )

        return StaticCredentialsResolver(
            AWSCredentialsIdentity(
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                session_token=config_file.get(profile_name, _SESSION_TOKEN),
                account_id=config_file.get(profile_name, _ACCOUNT_ID),
            )
        )

    async def _create_resolver_from_credential_source(
        self,
        credential_source: str,
        region: str,
    ) -> AWSCredentialsResolver:
        slot = _CREDENTIAL_SOURCE_SLOTS.get(credential_source)
        if slot is None:
            raise AssumeRoleConfigurationError(
                f"Unsupported 'credential_source': '{credential_source}'."
            )

        provider = self._find_provider(slot)
        if provider is None:
            raise AssumeRoleConfigurationError(
                f"No provider is installed for credential source '{credential_source}'. Install '{slot.module_suggestion}'."
            )

        setup = ChainSetup(
            region_override=region,
            http_client=self._http_client,
        )
        setup.set_current_provider(provider)
        await provider.setup(AWSCredentialsIdentity, setup)
        if not setup.resolvers:
            raise AssumeRoleConfigurationError(
                f"'{credential_source}' credential source is not configured."
            )
        return cast(AWSCredentialsResolver, setup.resolvers[0])

    def _find_provider(
        self,
        slot: StandardProvider,
    ) -> ChainIdentityProvider | None:
        for entry_point in metadata.entry_points(
            group=_CHAIN_PROVIDER_ENTRY_POINT_GROUP
        ):
            if entry_point.name != slot.canonical_name:
                continue
            provider_factory = cast(
                Callable[[], ChainIdentityProvider],
                entry_point.load(),
            )
            return provider_factory()
        return None

    def _parse_duration_seconds(self, profile_name: str) -> int | None:
        duration_seconds = self._config_file.get(profile_name, _DURATION_SECONDS)
        if duration_seconds is None:
            return None
        try:
            return int(duration_seconds)
        except ValueError:
            return None
