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
        self._http_client = http_client or AIOHTTPClient()
        self._imds_client = AsyncIMDSClient(
            http_client=self._http_client, config=config
        )
        self._config = config or IMDSConfig()
        self._credentials: AWSCredentialsIdentity | None = None

    async def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from IMDS."""
        if self._credentials is not None and is_fresh(self._credentials):
            return self._credentials
        self._credentials = await run_program_async(
            resolve_credentials(
                get=lambda path: self._imds_client.get(path=path),
                instance_profile_name=self._config.ec2_instance_profile_name,
            )
        )
        return self._credentials
