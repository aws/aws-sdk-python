# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Container credential rules shared by the sync and async resolvers."""

import ipaddress
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_core import URI
from smithy_core.exceptions import SmithyIdentityError
from smithy_core.program import Program
from smithy_http import Field, Fields, HTTPRequest
from smithy_http.interfaces import HTTPRequestConfiguration

RELATIVE_URI_ENV = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
FULL_URI_ENV = "AWS_CONTAINER_CREDENTIALS_FULL_URI"
AUTH_TOKEN_ENV = "AWS_CONTAINER_AUTHORIZATION_TOKEN"  # noqa: S105
AUTH_TOKEN_FILE_ENV = "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE"  # noqa: S105

DEFAULT_TIMEOUT = 2
DEFAULT_RETRIES = 3

_CONTAINER_METADATA_IP = "169.254.170.2"
_CONTAINER_METADATA_ALLOWED_HOSTS = {
    _CONTAINER_METADATA_IP,
    "169.254.170.23",
    "fd00:ec2::23",
    "localhost",
}
_SLEEP_SECONDS = 1


def is_configured() -> bool:
    return bool(os.getenv(RELATIVE_URI_ENV) or os.getenv(FULL_URI_ENV))


def is_fresh(credentials: AWSCredentialsIdentity | None) -> bool:
    return (
        credentials is not None
        and credentials.expiration is not None
        and datetime.now(UTC) < credentials.expiration
    )


def read_token_file(filename: str) -> str:
    with open(filename) as token_file:
        try:
            return token_file.read().strip()
        except UnicodeDecodeError as error:
            raise SmithyIdentityError(
                f"Unable to read valid utf-8 bytes from {filename}."
            ) from error


def fetch_credentials(
    *,
    send: Callable[[HTTPRequest, HTTPRequestConfiguration], Any],
    read_body: Callable[[Any], Any],
    sleep: Callable[[float], Any],
    uri: URI,
    fields: Fields,
    timeout: int,
    retries: int,
) -> Program[dict[str, str]]:
    """Fetch the credentials document, retrying failed attempts."""
    _validate_allowed_url(uri)
    fields.set_field(Field(name="Accept", values=["application/json"]))
    request_config = HTTPRequestConfiguration(read_timeout=timeout)

    attempts = 0
    last_exc = None
    while attempts < retries:
        try:
            request = HTTPRequest(method="GET", destination=uri, fields=fields)
            response = yield lambda: send(request, request_config)
            body: bytes = yield lambda: read_body(response.body)
            return _parse_document(response.status, body)
        except Exception as error:
            last_exc = error
            attempts += 1
            if attempts < retries:
                yield lambda: sleep(_SLEEP_SECONDS)

    raise SmithyIdentityError(
        f"Failed to retrieve container metadata after {retries} attempt(s)"
    ) from last_exc


def resolve_credentials(
    *,
    fetch: Callable[[URI, Fields], Any],
    read_token: Callable[[str], Any],
) -> Program[AWSCredentialsIdentity]:
    """Resolve credentials from the endpoint the environment configures."""
    uri = _resolve_uri()
    fields = Fields()
    if AUTH_TOKEN_FILE_ENV in os.environ:
        filename = os.environ[AUTH_TOKEN_FILE_ENV]
        try:
            auth_token: str = yield lambda: read_token(filename)
        except (FileNotFoundError, PermissionError) as error:
            raise SmithyIdentityError(f"Unable to open {filename}.") from error
        fields.set_field(_build_auth_field(auth_token))
    elif AUTH_TOKEN_ENV in os.environ:
        fields.set_field(_build_auth_field(os.environ[AUTH_TOKEN_ENV]))

    document: dict[str, str] = yield lambda: fetch(uri, fields)
    return _parse_identity(document)


def _resolve_uri() -> URI:
    if RELATIVE_URI_ENV in os.environ:
        return URI(
            scheme="http",
            host=_CONTAINER_METADATA_IP,
            path=os.environ[RELATIVE_URI_ENV],
        )
    if FULL_URI_ENV in os.environ:
        parsed = urlparse(os.environ[FULL_URI_ENV])
        return URI(
            scheme=parsed.scheme,
            host=parsed.hostname or "",
            port=parsed.port,
            path=parsed.path,
            query=parsed.query or None,
        )
    raise SmithyIdentityError(
        f"Neither {RELATIVE_URI_ENV} or {FULL_URI_ENV} environment "
        "variables are set. Unable to resolve credentials."
    )


def _build_auth_field(auth_token: str) -> Field:
    if "\r" in auth_token or "\n" in auth_token:
        raise SmithyIdentityError("Auth token value is not a legal header value.")
    return Field(name="Authorization", values=[auth_token])


def _parse_document(status: int, body: bytes) -> dict[str, str]:
    if status != 200:
        raise SmithyIdentityError(
            f"Container metadata service returned {status}: {body.decode('utf-8')}"
        )
    try:
        return json.loads(body.decode("utf-8"))
    except Exception as error:
        raise SmithyIdentityError(
            f"Unable to parse JSON from container metadata: {body.decode('utf-8')}"
        ) from error


def _parse_identity(document: dict[str, str]) -> AWSCredentialsIdentity:
    access_key_id = document.get("AccessKeyId")
    secret_access_key = document.get("SecretAccessKey")
    expiration = document.get("Expiration")
    if access_key_id is None or secret_access_key is None:
        raise SmithyIdentityError(
            "AccessKeyId and SecretAccessKey are required for container credentials"
        )
    return AWSCredentialsIdentity(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=document.get("Token"),
        expiration=(
            datetime.fromisoformat(expiration).replace(tzinfo=UTC)
            if isinstance(expiration, str)
            else None
        ),
        account_id=document.get("AccountId"),
    )


def _validate_allowed_url(uri: URI) -> None:
    if uri.scheme == "https" or _is_loopback(uri.host):
        return
    if uri.host not in _CONTAINER_METADATA_ALLOWED_HOSTS:
        raise SmithyIdentityError(
            f"Unsupported host '{uri.host}'. "
            f"Can only retrieve metadata from an HTTPS endpoint, a loopback "
            f"address, or one of: {', '.join(_CONTAINER_METADATA_ALLOWED_HOSTS)}"
        )


def _is_loopback(hostname: str) -> bool:
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False
