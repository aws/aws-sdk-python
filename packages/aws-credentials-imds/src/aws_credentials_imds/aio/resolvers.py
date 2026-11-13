# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.aio.interfaces.identity import AsyncIdentityResolver
from smithy_core.aio.program import run_program_async
from smithy_http.aio.aiohttp import AIOHTTPClient
from smithy_http.aio.interfaces import AsyncHTTPClient

from .._imds import IMDSConfig, is_fresh, resolve_credentials
from .client import AsyncIMDSClient


class AsyncIMDSCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves AWS credentials from the EC2 Instance Metadata Service."""

    def __init__(
        self,
        http_client: AsyncHTTPClient | None = None,
        config: IMDSConfig | None = None,
    ):
        self._config = config or IMDSConfig()
        # A caller-provided client is the caller's to close.
        self._imds_client = (
            AsyncIMDSClient(http_client=http_client, config=self._config)
            if http_client is not None
            else None
        )
        self._credentials: AWSCredentialsIdentity | None = None

    async def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from IMDS."""
        if self._credentials is not None and is_fresh(self._credentials):
            return self._credentials
        if self._imds_client is not None:
            self._credentials = await self._resolve(self._imds_client)
        else:
            async with AIOHTTPClient() as http_client:
                self._credentials = await self._resolve(
                    AsyncIMDSClient(http_client=http_client, config=self._config)
                )
        return self._credentials

    async def _resolve(self, imds_client: AsyncIMDSClient) -> AWSCredentialsIdentity:
        return await run_program_async(
            resolve_credentials(
                get=lambda path: imds_client.get(path=path),
                instance_profile_name=self._config.ec2_instance_profile_name,
            )
        )
