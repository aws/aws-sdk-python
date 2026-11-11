# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import os
from pathlib import Path
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
from smithy_core.auth import NoAuthResolver
from smithy_core.exceptions import SmithyIdentityError
from smithy_core.retries import StandardRetryStrategy
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
from .._web_identity import (
    DEFAULT_ROLE_SESSION_NAME,
    MAX_RETRIES,
    UNUSED_CREDENTIALS_MESSAGE,
    read_token,
    web_identity_input,
)
from .._web_identity import identity_from_response as web_identity_from_response

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


class _AsyncUnusedCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """The credentials resolver for the STS client that calls AssumeRoleWithWebIdentity.

    The call is never signed, so this is never asked for credentials. Setting it
    keeps the STS client from building its own default credential chain, which
    would include the web identity providers again.
    """

    async def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        raise SmithyIdentityError(UNUSED_CREDENTIALS_MESSAGE)


class AsyncWebIdentityCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves credentials with an STS AssumeRoleWithWebIdentity call.

    The OIDC token is read from ``web_identity_token_file`` each time the credentials
    are refreshed, so a token that is rotated on disk is picked up.

    :param role_arn: The ARN of the role to assume.
    :param web_identity_token_file: The path of the file that contains the OIDC
        token. A relative path is relative to the process's working directory.
    :param role_session_name: The name of the role session. When it isn't set, a
        name generated once per process is used.
    :param region: The region of the STS endpoint to call. When it isn't set, it's
        taken from ``AWS_REGION`` or ``AWS_DEFAULT_REGION``, then ``us-east-1``.
    :param http_client: The HTTP client to call STS with.
    """

    def __init__(
        self,
        *,
        role_arn: str,
        web_identity_token_file: str | os.PathLike[str],
        role_session_name: str | None = None,
        region: str | None = None,
        http_client: AsyncHTTPClient | None = None,
    ) -> None:
        self._role_arn = role_arn
        self._web_identity_token_file = Path(web_identity_token_file)
        self._role_session_name = role_session_name or DEFAULT_ROLE_SESSION_NAME
        self._region = region or resolve_sts_region()
        self._http_client = http_client
        self._credentials: AWSCredentialsIdentity | None = None
        self._client: AsyncSTSClient | None = None
        self._refresh_lock = asyncio.Lock()
        # Wait between attempts the same way the SDK's standard retry strategy does.
        self._backoff = StandardRetryStrategy().backoff_strategy

    async def get_identity(
        self,
        *,
        properties: AWSIdentityProperties,
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise call STS for new ones."""
        if self._credentials is not None and not self._credentials.is_expired:
            return self._credentials

        async with self._refresh_lock:
            if self._credentials is not None and not self._credentials.is_expired:
                return self._credentials
            self._credentials = await self._assume_role_with_web_identity()
            return self._credentials

    async def invalidate(self) -> None:
        """Discard the cached credentials so the next call fetches new ones."""
        async with self._refresh_lock:
            self._credentials = None

    async def _assume_role_with_web_identity(self) -> AWSCredentialsIdentity:
        from aws_sdk_sts.aio.client import AsyncSTSClient
        from aws_sdk_sts.aio.config import AsyncSTSConfig

        overrides: AsyncAwsConfigOverrides = {
            "region": self._region,
            "aws_credentials_identity_resolver": _AsyncUnusedCredentialsResolver(),
        }
        # The call must be unsigned. The generated STS auth resolver doesn't
        # recognize the operation, so it would otherwise be signed.
        auth_scheme_resolver = NoAuthResolver()
        if self._client is None and self._http_client is not None:
            # CAUTION: never closed, since closing it would close the caller's transport.
            overrides["transport"] = self._http_client
            self._client = AsyncSTSClient(
                config=await AsyncSTSConfig.resolve(
                    **overrides, auth_scheme_resolver=auth_scheme_resolver
                )
            )
        if self._client is not None:
            return await self._call(self._client)
        config = await AsyncSTSConfig.resolve(
            **overrides, auth_scheme_resolver=auth_scheme_resolver
        )
        try:
            async with AsyncSTSClient(config=config) as client:
                return await self._call(client)
        finally:
            # The client closes its transport only after it sends a request. Close it
            # here too, in case the token couldn't be read and nothing was sent.
            if (close := getattr(config.transport, "close", None)) is not None:
                await close()

    async def _call(self, client: AsyncSTSClient) -> AWSCredentialsIdentity:
        """Call STS, retrying the failures the web identity SEP requires.

        A failure to read the token file and an ``ExpiredTokenException`` both read
        the token again before retrying. An ``IDPCommunicationError`` retries the STS
        call with the same token. Other errors are raised immediately.
        """
        from aws_sdk_sts.models import (
            ExpiredTokenException,
            IDPCommunicationErrorException,
        )

        token: str | None = None
        for attempt in range(MAX_RETRIES + 1):
            is_last_attempt = attempt == MAX_RETRIES
            if token is None:
                # Read the file in a thread so a slow disk doesn't block the loop.
                token = await asyncio.to_thread(
                    read_token,
                    self._web_identity_token_file,
                    is_last_attempt=is_last_attempt,
                )
            if token is not None:
                try:
                    response = await client.assume_role_with_web_identity(
                        web_identity_input(
                            role_arn=self._role_arn,
                            role_session_name=self._role_session_name,
                            web_identity_token=token,
                        )
                    )
                except ExpiredTokenException:
                    if is_last_attempt:
                        raise
                    token = None  # Read a fresh token before retrying.
                except IDPCommunicationErrorException:
                    if is_last_attempt:
                        raise
                else:
                    return web_identity_from_response(response)
            await asyncio.sleep(self._backoff.compute_next_backoff_delay(attempt + 1))

        raise AssertionError("unreachable")
