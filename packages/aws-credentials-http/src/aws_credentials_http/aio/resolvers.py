# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio
import os
from datetime import UTC, datetime
from urllib.parse import urlparse

from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core import URI
from smithy_core.aio.interfaces.identity import AsyncIdentityResolver
from smithy_core.exceptions import SmithyIdentityError
from smithy_http import Field, Fields
from smithy_http.aio.aiohttp import AIOHTTPClient
from smithy_http.aio.interfaces import AsyncHTTPClient

from .client import HttpCredentialsClient

_CONTAINER_METADATA_IP = "169.254.170.2"
_DEFAULT_TIMEOUT = 2
_DEFAULT_RETRIES = 3


class ContainerCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves AWS credentials from container HTTP endpoints."""

    ENV_VAR = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
    ENV_VAR_FULL = "AWS_CONTAINER_CREDENTIALS_FULL_URI"
    ENV_VAR_AUTH_TOKEN = "AWS_CONTAINER_AUTHORIZATION_TOKEN"  # noqa: S105
    ENV_VAR_AUTH_TOKEN_FILE = "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"  # noqa: S105

    def __init__(
        self,
        http_client: AsyncHTTPClient | None = None,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
    ):
        self._http_client = http_client or AIOHTTPClient()
        self._client = HttpCredentialsClient(
            self._http_client, timeout=timeout, retries=retries
        )
        self._credentials = None

    async def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from container endpoint."""
        if (
            self._credentials is not None
            and self._credentials.expiration
            and datetime.now(UTC) < self._credentials.expiration
        ):
            return self._credentials

        uri = await self._resolve_uri_from_env()
        fields = await self._resolve_fields_from_env()
        creds = await self._client.get_credentials(uri, fields)

        access_key_id = creds.get("AccessKeyId")
        secret_access_key = creds.get("SecretAccessKey")
        session_token = creds.get("Token")
        expiration = creds.get("Expiration")
        account_id = creds.get("AccountId")

        if isinstance(expiration, str):
            expiration = datetime.fromisoformat(expiration).replace(tzinfo=UTC)

        if access_key_id is None or secret_access_key is None:
            raise SmithyIdentityError(
                "AccessKeyId and SecretAccessKey are required for container credentials"
            )

        self._credentials = AWSCredentialsIdentity(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            expiration=expiration,
            account_id=account_id,
        )
        return self._credentials

    async def _resolve_uri_from_env(self) -> URI:
        if self.ENV_VAR in os.environ:
            return URI(
                scheme="http",
                host=_CONTAINER_METADATA_IP,
                path=os.environ[self.ENV_VAR],
            )
        elif self.ENV_VAR_FULL in os.environ:
            parsed = urlparse(os.environ[self.ENV_VAR_FULL])
            return URI(
                scheme=parsed.scheme,
                host=parsed.hostname or "",
                port=parsed.port,
                path=parsed.path,
                query=parsed.query or None,
            )
        else:
            raise SmithyIdentityError(
                f"Neither {self.ENV_VAR} or {self.ENV_VAR_FULL} environment "
                "variables are set. Unable to resolve credentials."
            )

    async def _resolve_fields_from_env(self) -> Fields:
        fields = Fields()
        if self.ENV_VAR_AUTH_TOKEN_FILE in os.environ:
            try:
                filename = os.environ[self.ENV_VAR_AUTH_TOKEN_FILE]
                auth_token = await asyncio.to_thread(self._read_file, filename)
            except (FileNotFoundError, PermissionError) as error:
                raise SmithyIdentityError(
                    f"Unable to open {os.environ[self.ENV_VAR_AUTH_TOKEN_FILE]}."
                ) from error

            fields.set_field(self._build_auth_field(auth_token))
        elif self.ENV_VAR_AUTH_TOKEN in os.environ:
            auth_token = os.environ[self.ENV_VAR_AUTH_TOKEN]
            fields.set_field(self._build_auth_field(auth_token))

        return fields

    def _build_auth_field(self, auth_token: str) -> Field:
        if "\r" in auth_token or "\n" in auth_token:
            raise SmithyIdentityError("Auth token value is not a legal header value.")
        return Field(name="Authorization", values=[auth_token])

    def _read_file(self, filename: str) -> str:
        with open(filename) as token_file:
            try:
                return token_file.read().strip()
            except UnicodeDecodeError as error:
                raise SmithyIdentityError(
                    f"Unable to read valid utf-8 bytes from {filename}."
                ) from error
