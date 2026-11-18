# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""IMDS rules shared by the sync and async clients, resolvers and providers."""

import functools
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import Any, Literal
from urllib.parse import urlsplit

from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_core import URI
from smithy_core.exceptions import SmithyError, SmithyIdentityError
from smithy_core.program import Program
from smithy_http import Field, Fields, HTTPRequest
from smithy_http.interfaces import HTTPRequestConfiguration

_TOKEN_PATH = "/latest/api/token"  # noqa: S105
_TOKEN_TTL_HEADER = "x-aws-ec2-metadata-token-ttl-seconds"  # noqa: S105
_METADATA_PATH_BASE = "/latest/meta-data/iam/security-credentials"

_DISABLED_ENV = "AWS_EC2_METADATA_DISABLED"
_DISABLED_PROFILE = "disable_ec2_metadata"
_ENDPOINT_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT"
_ENDPOINT_PROFILE = "ec2_metadata_service_endpoint"
_ENDPOINT_MODE_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE"
_ENDPOINT_MODE_PROFILE = "ec2_metadata_service_endpoint_mode"
_PROFILE_NAME_ENV = "AWS_EC2_INSTANCE_PROFILE_NAME"
_PROFILE_NAME_PROFILE = "ec2_instance_profile_name"
_MAX_ATTEMPTS_ENV = "AWS_METADATA_SERVICE_NUM_ATTEMPTS"
_MAX_ATTEMPTS_PROFILE = "metadata_service_num_attempts"

# 3 retries, so 4 attempts in all.
DEFAULT_MAX_ATTEMPTS = 4
# IMDS is a link-local endpoint, so a healthy instance answers well within a second.
TIMEOUT_SECONDS = 1.0
_REQUEST_CONFIG = HTTPRequestConfiguration(read_timeout=TIMEOUT_SECONDS)
# Waits of 0.25 s, 0.5 s and 1 s across the default 3 retries.
_BACKOFF_BASE_SECONDS = 0.25
_MAX_BACKOFF_SECONDS = 1.0


class IMDSConfigurationError(SmithyError):
    """Raised when IMDS credential configuration is invalid."""


@dataclass(init=False)
class IMDSConfig:
    """Configuration for IMDSClient."""

    _HOST_MAPPING = MappingProxyType(
        {"IPv4": "169.254.169.254", "IPv6": "[fd00:ec2::254]"}
    )
    _MIN_TTL = 5
    _MAX_TTL = 21600

    max_attempts: int
    endpoint_uri: URI
    endpoint_mode: Literal["IPv4", "IPv6"]
    token_ttl: int

    def __init__(
        self,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        endpoint_uri: URI | None = None,
        endpoint_mode: Literal["IPv4", "IPv6"] = "IPv4",
        token_ttl: int = _MAX_TTL,
        ec2_instance_profile_name: str | None = None,
    ):
        self.max_attempts = self._validate_max_attempts(max_attempts)
        self.endpoint_mode = endpoint_mode
        self.endpoint_uri = self._resolve_endpoint(endpoint_uri, endpoint_mode)
        self.token_ttl = self._validate_token_ttl(token_ttl)
        self.ec2_instance_profile_name = ec2_instance_profile_name

    def _validate_max_attempts(self, max_attempts: int) -> int:
        # bool is an int subclass, but True is not a meaningful attempt count.
        if (
            isinstance(max_attempts, bool)
            or not isinstance(max_attempts, int)
            or max_attempts < 1
        ):
            raise IMDSConfigurationError(
                f"IMDS max attempts must be an integer of at least 1, got {max_attempts!r}."
            )
        return max_attempts

    def _validate_token_ttl(self, ttl: int) -> int:
        if not self._MIN_TTL <= ttl <= self._MAX_TTL:
            raise IMDSConfigurationError(
                f"Token TTL must be between {self._MIN_TTL} and {self._MAX_TTL} seconds."
            )
        return ttl

    def _resolve_endpoint(
        self, endpoint_uri: URI | None, endpoint_mode: Literal["IPv4", "IPv6"]
    ) -> URI:
        if endpoint_uri is not None:
            return endpoint_uri

        return URI(
            scheme="http",
            host=self._HOST_MAPPING.get(endpoint_mode, self._HOST_MAPPING["IPv4"]),
            port=80,
        )


class IMDSToken:
    """Represents an IMDSv2 session token."""

    def __init__(self, value: str, ttl: int):
        self._value = value
        self._ttl = ttl
        self._created_time = datetime.now()

    def is_expired(self) -> bool:
        return datetime.now() - self._created_time >= timedelta(seconds=self._ttl)

    @property
    def value(self) -> str:
        return self._value


def is_fresh(credentials: AWSCredentialsIdentity | None) -> bool:
    return (
        credentials is not None
        and credentials.expiration is not None
        and datetime.now(UTC) < credentials.expiration
    )


def provider_config(
    config_file: MergedConfig | None, profile_name: str | None
) -> IMDSConfig | None:
    """Return the chain's IMDS config, or None when IMDS is disabled."""
    disabled = _resolve_value(
        config_file, profile_name, _DISABLED_ENV, _DISABLED_PROFILE
    )
    if disabled is not None and disabled.casefold() == "true":
        return None

    endpoint = _resolve_value(
        config_file, profile_name, _ENDPOINT_ENV, _ENDPOINT_PROFILE
    )
    endpoint_mode = _resolve_value(
        config_file, profile_name, _ENDPOINT_MODE_ENV, _ENDPOINT_MODE_PROFILE
    )
    instance_profile_name = _resolve_value(
        config_file, profile_name, _PROFILE_NAME_ENV, _PROFILE_NAME_PROFILE
    )
    max_attempts = _resolve_value(
        config_file, profile_name, _MAX_ATTEMPTS_ENV, _MAX_ATTEMPTS_PROFILE
    )
    return IMDSConfig(
        max_attempts=_parse_max_attempts(max_attempts),
        endpoint_uri=_parse_endpoint_uri(endpoint),
        endpoint_mode=_parse_endpoint_mode(endpoint_mode),
        ec2_instance_profile_name=_validate_profile_name(instance_profile_name),
    )


def fetch_token(
    *,
    send: Callable[[HTTPRequest, HTTPRequestConfiguration], Any],
    read_body: Callable[[Any], Any],
    config: IMDSConfig,
) -> Program[IMDSToken]:
    """Request an IMDSv2 session token.

    The token expires after the TTL IMDS reports in its response, which can differ
    from the one requested.
    """
    request = HTTPRequest(
        method="PUT",
        destination=_endpoint_path(config.endpoint_uri, _TOKEN_PATH),
        fields=Fields(
            [
                _user_agent_field(),
                Field(
                    name=_TOKEN_TTL_HEADER,
                    values=[str(config.token_ttl)],
                ),
            ]
        ),
    )
    status, fields, body = yield from _exchange(send, read_body, request)
    if status != 200:
        raise _IMDSRequestError(
            f"IMDS returned {status} when fetching a metadata token.",
            status=status,
            # Any other failure is retried. 400 and 403 mean IMDSv2 is unusable here,
            # so retrying can't help.
            retryable=status not in (400, 403),
        )
    return IMDSToken(body.decode("utf-8"), _response_ttl(fields, config.token_ttl))


def fetch_metadata(
    *,
    send: Callable[[HTTPRequest, HTTPRequestConfiguration], Any],
    read_body: Callable[[Any], Any],
    config: IMDSConfig,
    token: str,
    path: str,
) -> Program[str]:
    """Read one metadata path with an IMDSv2 session token."""
    request = HTTPRequest(
        method="GET",
        destination=_endpoint_path(config.endpoint_uri, path),
        fields=Fields(
            [
                _user_agent_field(),
                Field(name="x-aws-ec2-metadata-token", values=[token]),
            ]
        ),
    )
    status, _, body = yield from _exchange(send, read_body, request)
    if status != 200:
        raise _IMDSRequestError(
            f"IMDS returned {status} for path '{path}'.",
            status=status,
            # Any other failure is retried. A 404 means the path doesn't exist and a 403
            # that access is denied, which a retry can't change. A 401 means the token
            # was rejected, so a retry with a new token can pass.
            retryable=status not in (403, 404),
        )
    return body.decode("utf-8")


def get_metadata(
    *,
    send: Callable[[HTTPRequest, HTTPRequestConfiguration], Any],
    read_body: Callable[[Any], Any],
    sleep: Callable[[float], Any],
    get_token: Callable[[], Any],
    invalidate_token: Callable[[Any], Any],
    config: IMDSConfig,
    path: str,
) -> Program[str]:
    """Read one metadata path, retrying the token fetch and read as one unit.

    Any failed request is retried with capped exponential backoff until
    ``config.max_attempts`` attempts are used, except a token request answered with
    400 or 403 and a metadata request answered with 403 or 404. A response that
    can't be decoded is raised at once.
    """
    attempts = 0
    last_exc: Exception | None = None
    while attempts < config.max_attempts:
        token: Any = None
        try:
            token = yield get_token
            return (
                yield from fetch_metadata(
                    send=send,
                    read_body=read_body,
                    config=config,
                    token=token.value,
                    path=path,
                )
            )
        except _IMDSRequestError as error:
            if not error.retryable:
                raise
            if error.status == 401 and token is not None:
                # Drop the rejected token so the next attempt fetches a new one.
                yield lambda: invalidate_token(token)
            last_exc = error
        attempts += 1
        if attempts >= config.max_attempts:
            break
        delay = backoff_delay(attempts)
        yield lambda: sleep(delay)

    raise SmithyIdentityError(
        f"Failed to retrieve IMDS metadata for path '{path}' "
        f"after {attempts} attempt(s)."
    ) from last_exc


def backoff_delay(attempt: int) -> float:
    """Return the delay in seconds after the given failed attempt (1-based)."""
    return min(_MAX_BACKOFF_SECONDS, _BACKOFF_BASE_SECONDS * 2 ** (attempt - 1))


def resolve_credentials(
    *, get: Callable[[str], Any], instance_profile_name: str | None
) -> Program[AWSCredentialsIdentity]:
    """Resolve credentials for the configured or discovered instance profile."""
    profile = instance_profile_name
    if profile is None:
        profile = yield lambda: get(_METADATA_PATH_BASE)
    document: str = yield lambda: get(f"{_METADATA_PATH_BASE}/{profile}")
    return _parse_identity(json.loads(document))


def _response_ttl(fields: Fields, requested: int) -> int:
    """Return the token TTL from the response, or ``requested`` if IMDS sent none."""
    field = fields.get(_TOKEN_TTL_HEADER)
    if field is None:
        return requested
    try:
        ttl = int(field.as_string())
    except ValueError:
        return requested
    return ttl if ttl > 0 else requested


class _IMDSRequestError(SmithyIdentityError):
    """A failed IMDS request: an unexpected status, or no response (``status`` None)."""

    def __init__(self, message: str, *, status: int | None, retryable: bool):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


def _exchange(
    send: Callable[[HTTPRequest, HTTPRequestConfiguration], Any],
    read_body: Callable[[Any], Any],
    request: HTTPRequest,
) -> Program[tuple[int, Fields, bytes]]:
    """Send ``request`` and read its body, as one retryable step."""
    try:
        response = yield lambda: send(request, _REQUEST_CONFIG)
        body: bytes = yield lambda: read_body(response.body)
    except Exception as error:
        # A failure to get a response is retryable whatever the HTTP client raised:
        # refused, reset or dropped connections, and timeouts.
        raise _IMDSRequestError(
            f"IMDS request to {request.destination.path} failed: {error!r}",
            status=None,
            retryable=True,
        ) from error
    return response.status, response.fields, body


@functools.cache
def _user_agent_field() -> Field:
    # Deferred: the package __init__ imports this module, so a top-level import is a cycle.
    from . import __version__

    return Field(
        name="User-Agent", values=[f"aws-sdk-python-imds-client/{__version__}"]
    )


def _endpoint_path(endpoint: URI, path: str) -> URI:
    return URI(
        scheme=endpoint.scheme, host=endpoint.host, port=endpoint.port, path=path
    )


def _parse_identity(document: dict[str, Any]) -> AWSCredentialsIdentity:
    access_key_id = document.get("AccessKeyId")
    secret_access_key = document.get("SecretAccessKey")
    expiration = document.get("Expiration")
    if access_key_id is None or secret_access_key is None:
        raise SmithyIdentityError("AccessKeyId and SecretAccessKey are required")
    return AWSCredentialsIdentity(
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=document.get("Token"),
        expiration=(
            datetime.fromisoformat(expiration).replace(tzinfo=UTC)
            if expiration is not None
            else None
        ),
        account_id=document.get("AccountId"),
    )


def _resolve_value(
    config_file: MergedConfig | None,
    profile_name: str | None,
    env_name: str,
    profile_key: str,
) -> str | None:
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    if config_file is None or profile_name is None:
        return None
    return config_file.get(profile_name, profile_key)


def _parse_endpoint_uri(value: str | None) -> URI | None:
    if value is None:
        return None

    try:
        parsed = urlsplit(value)

        if not parsed.scheme or parsed.hostname is None:
            raise ValueError

        # Access validates the port value and range
        port = parsed.port
    except ValueError as error:
        raise IMDSConfigurationError(f"Invalid IMDS endpoint URI: {value}") from error

    return URI(scheme=parsed.scheme, host=parsed.hostname, port=port)


def _parse_endpoint_mode(value: str | None) -> Literal["IPv4", "IPv6"]:
    if value is None:
        return "IPv4"

    normalized = value.casefold()
    if normalized == "ipv4":
        return "IPv4"
    if normalized == "ipv6":
        return "IPv6"
    raise IMDSConfigurationError(
        f"Invalid IMDS endpoint mode {value!r}; expected 'IPv4' or 'IPv6'."
    )


def _parse_max_attempts(value: str | None) -> int:
    if value is None:
        return DEFAULT_MAX_ATTEMPTS
    try:
        return int(value)
    except ValueError as error:
        raise IMDSConfigurationError(
            f"Invalid IMDS max attempts {value!r}; expected a positive integer."
        ) from error


def _validate_profile_name(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise IMDSConfigurationError(
            "The configured EC2 instance profile name must not be blank."
        )
    return value
