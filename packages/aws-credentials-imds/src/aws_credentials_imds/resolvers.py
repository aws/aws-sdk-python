# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.interfaces.identity import IdentityResolver
from smithy_core.program import run_program
from smithy_http.interfaces import HTTPClient
from smithy_http.urllib3 import Urllib3HTTPClient, Urllib3HTTPClientConfig

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
        """
        :param http_client: HTTP client for IMDS requests. It keeps its own connect
            timeout. Defaults to a client the resolver creates once and keeps, with
            ``config.timeout`` as its connect and read timeouts.
        :param config: IMDS configuration. Defaults to ``IMDSConfig()``.
        """
        self._config = config or IMDSConfig()
        if http_client is None:
            # Created once and kept, so the session token is reused across calls.
            http_client = Urllib3HTTPClient(
                client_config=Urllib3HTTPClientConfig(
                    connect_timeout=self._config.timeout,
                    read_timeout=self._config.timeout,
                )
            )
        self._imds_client = IMDSClient(http_client=http_client, config=self._config)
        self._credentials: AWSCredentialsIdentity | None = None

    def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from IMDS."""
        if self._credentials is not None and is_fresh(self._credentials):
            return self._credentials
        self._credentials = run_program(
            resolve_credentials(
                get=lambda path: self._imds_client.get(path=path),
                instance_profile_name=self._config.ec2_instance_profile_name,
            )
        )
        return self._credentials
