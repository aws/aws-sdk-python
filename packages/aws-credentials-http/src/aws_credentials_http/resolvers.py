# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.interfaces.identity import IdentityResolver
from smithy_core.program import run_program
from smithy_http.interfaces import HTTPClient
from smithy_http.urllib3 import Urllib3HTTPClient

from ._container import (
    AUTH_TOKEN_ENV,
    AUTH_TOKEN_FILE_ENV,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    FULL_URI_ENV,
    RELATIVE_URI_ENV,
    is_fresh,
    read_token_file,
    resolve_credentials,
)
from .client import HttpCredentialsClient


class ContainerCredentialsResolver(
    IdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves AWS credentials from container HTTP endpoints."""

    ENV_VAR = RELATIVE_URI_ENV
    ENV_VAR_FULL = FULL_URI_ENV
    ENV_VAR_AUTH_TOKEN = AUTH_TOKEN_ENV
    ENV_VAR_AUTH_TOKEN_FILE = AUTH_TOKEN_FILE_ENV

    def __init__(
        self,
        http_client: HTTPClient | None = None,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self._timeout = timeout
        self._retries = retries
        # A caller-provided client is the caller's to close.
        self._client = (
            HttpCredentialsClient(http_client, timeout=timeout, retries=retries)
            if http_client is not None
            else None
        )
        self._credentials: AWSCredentialsIdentity | None = None

    def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from container endpoint."""
        if self._credentials is not None and is_fresh(self._credentials):
            return self._credentials
        if self._client is not None:
            self._credentials = self._resolve(self._client)
        else:
            with Urllib3HTTPClient() as http_client:
                self._credentials = self._resolve(
                    HttpCredentialsClient(
                        http_client, timeout=self._timeout, retries=self._retries
                    )
                )
        return self._credentials

    def _resolve(self, client: HttpCredentialsClient) -> AWSCredentialsIdentity:
        return run_program(
            resolve_credentials(
                fetch=client.get_credentials, read_token=read_token_file
            )
        )
