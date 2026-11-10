# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from smithy_aws_core.aio.config import AsyncAwsConfigOverrides
from smithy_aws_core.aio.identity import (
    AsyncAWSCredentialsResolver,
    AsyncStaticCredentialsResolver,
)
from smithy_aws_core.aio.identity.chain.provider import (
    AsyncChainIdentityProvider,
    AsyncChainSetup,
)
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_aws_core.identity.chain import StandardProvider
from smithy_core.aio.interfaces.identity import AsyncIdentityResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from .._assume_role import (
    DEFAULT_STS_REGION,
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
    from aws_sdk_sts.aio.client import AsyncSTSClient

_CHAIN_PROVIDER_ENTRY_POINT_GROUP = "smithy_aws_core.aio.identity.chain_providers"


class AsyncAssumeRoleCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves credentials with an STS AssumeRole call."""

    def __init__(
        self,
        *,
        source_resolver: AsyncAWSCredentialsResolver,
        role_arn: str,
        role_session_name: str | None = None,
        external_id: str | None = None,
        duration_seconds: int | None = None,
        region: str | None = None,
        http_client: AsyncHTTPClient | None = None,
    ) -> None:
        self._source_resolver = source_resolver
        self._role_arn = role_arn
        self._role_session_name = role_session_name or default_session_name()
        self._external_id = external_id
        self._duration_seconds = duration_seconds
        self._region = region or DEFAULT_STS_REGION
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
        from aws_sdk_sts.aio.client import AsyncSTSClient
        from aws_sdk_sts.aio.config import AsyncSTSConfig

        overrides: AsyncAwsConfigOverrides = {
            "aws_credentials_identity_resolver": self._source_resolver,
            "region": self._region,
        }
        if self._client is None and self._http_client is not None:
            # CAUTION: never closed, since closing it would close the caller's transport.
            overrides["transport"] = self._http_client
            self._client = AsyncSTSClient(
                config=await AsyncSTSConfig.resolve(**overrides)
            )
        if self._client is not None:
            return await self._call(self._client)
        async with AsyncSTSClient(
            config=await AsyncSTSConfig.resolve(**overrides)
        ) as client:
            return await self._call(client)

    async def _call(self, client: AsyncSTSClient) -> AWSCredentialsIdentity:
        response = await client.assume_role(
            assume_role_input(
                role_arn=self._role_arn,
                role_session_name=self._role_session_name,
                external_id=self._external_id,
                duration_seconds=self._duration_seconds,
            )
        )
        return identity_from_response(response)


class AsyncProfileAssumeRoleCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves credentials from a profile-based AssumeRole configuration."""

    def __init__(
        self,
        *,
        profile_name: str,
        config_file: MergedConfig,
        region_override: str | None = None,
        http_client: AsyncHTTPClient | None = None,
    ) -> None:
        validate_profile(config_file, profile_name)
        self._profile_name = profile_name
        self._config_file = config_file
        self._region = region_override or resolve_sts_region(
            config_file=config_file, profile_name=profile_name
        )
        self._http_client = http_client
        self._delegate: AsyncAssumeRoleCredentialsResolver | None = None
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
                    self._delegate = await self._create_delegate()
        return await self._delegate.get_identity(properties=properties)

    async def _create_delegate(self) -> AsyncAssumeRoleCredentialsResolver:
        return await self._build_assume_role(
            plan_profile(self._config_file, self._profile_name)
        )

    def _find_provider(
        self, slot: StandardProvider
    ) -> AsyncChainIdentityProvider | None:
        return find_provider(_CHAIN_PROVIDER_ENTRY_POINT_GROUP, slot)

    async def _build_assume_role(
        self, plan: AssumeRolePlan
    ) -> AsyncAssumeRoleCredentialsResolver:
        return AsyncAssumeRoleCredentialsResolver(
            source_resolver=await self._build_source(plan.source),
            role_arn=plan.role_arn,
            role_session_name=plan.role_session_name,
            external_id=plan.external_id,
            duration_seconds=plan.duration_seconds,
            region=self._region,
            http_client=self._http_client,
        )

    async def _build_source(
        self, source: StaticSource | CredentialSource | AssumeRolePlan
    ) -> AsyncAWSCredentialsResolver:
        match source:
            case StaticSource(identity=identity):
                return AsyncStaticCredentialsResolver(identity)
            case CredentialSource():
                provider = require_provider(self._find_provider(source.slot), source)
                setup = AsyncChainSetup(
                    region_override=self._region, http_client=self._http_client
                )
                setup.set_current_provider(provider)
                await provider.setup(AWSCredentialsIdentity, setup)
                return first_resolver(setup.resolvers, source)
            case AssumeRolePlan():
                return await self._build_assume_role(source)
