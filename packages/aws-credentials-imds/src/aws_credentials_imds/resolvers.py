# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.interfaces.identity import IdentityResolver
from smithy_core.program import run_program
from smithy_http.interfaces import HTTPClient
from smithy_http.urllib3 import Urllib3HTTPClient

from ._imds import IMDSConfig, is_fresh, resolve_credentials
from .client import IMDSClient


class IMDSCredentialsResolver(
    IdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves AWS credentials from the EC2 Instance Metadata Service."""

    def __init__(
        self,
        http_client: HTTPClient | None = None,
        config: IMDSConfig | None = None,
    ):
        self._config = config or IMDSConfig()
        # A caller-provided client is the caller's to close.
        self._imds_client = (
            IMDSClient(http_client=http_client, config=self._config)
            if http_client is not None
            else None
        )
        self._credentials: AWSCredentialsIdentity | None = None

    def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from IMDS."""
        if self._credentials is not None and is_fresh(self._credentials):
            return self._credentials
        if self._imds_client is not None:
            self._credentials = self._resolve(self._imds_client)
        else:
            with Urllib3HTTPClient() as http_client:
                self._credentials = self._resolve(
                    IMDSClient(http_client=http_client, config=self._config)
                )
        return self._credentials

    def _resolve(self, imds_client: IMDSClient) -> AWSCredentialsIdentity:
        return run_program(
            resolve_credentials(
                get=lambda path: imds_client.get(path=path),
                instance_profile_name=self._config.ec2_instance_profile_name,
            )
        )
