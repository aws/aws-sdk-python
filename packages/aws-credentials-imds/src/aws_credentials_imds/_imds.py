# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""IMDS rules shared by the sync and async clients, resolvers and providers."""

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
from smithy_core.interfaces.retries import RetryStrategy
from smithy_core.program import Program
from smithy_core.retries import SimpleRetryStrategy
from smithy_http import Field, Fields, HTTPRequest

from . import __version__

_USER_AGENT_FIELD = Field(
    name="User-Agent",
    values=[f"aws-sdk-python-imds-client/{__version__}"],
)
_TOKEN_PATH = "/latest/api/token"  # noqa: S105
_METADATA_PATH_BASE = "/latest/meta-data/iam/security-credentials"

_DISABLED_ENV = "AWS_EC2_METADATA_DISABLED"
_DISABLED_PROFILE = "disable_ec2_metadata"
_ENDPOINT_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT"
_ENDPOINT_PROFILE = "ec2_metadata_service_endpoint"
_ENDPOINT_MODE_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE"
_ENDPOINT_MODE_PROFILE = "ec2_metadata_service_endpoint_mode"
_PROFILE_NAME_ENV = "AWS_EC2_INSTANCE_PROFILE_NAME"
_PROFILE_NAME_PROFILE = "ec2_instance_profile_name"


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

    retry_strategy: RetryStrategy
    endpoint_uri: URI
    endpoint_mode: Literal["IPv4", "IPv6"]
    token_ttl: int

    def __init__(
        self,
        *,
        retry_strategy: RetryStrategy | None = None,
        endpoint_uri: URI | None = None,
        endpoint_mode: Literal["IPv4", "IPv6"] = "IPv4",
        token_ttl: int = _MAX_TTL,
        ec2_instance_profile_name: str | None = None,
    ):
        # TODO: Implement IMDS request retries.
        self.retry_strategy = retry_strategy or SimpleRetryStrategy(max_attempts=3)
        self.endpoint_mode = endpoint_mode
        self.endpoint_uri = self._resolve_endpoint(endpoint_uri, endpoint_mode)
        self.token_ttl = self._validate_token_ttl(token_ttl)
        self.ec2_instance_profile_name = ec2_instance_profile_name

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
    return IMDSConfig(
        endpoint_uri=_parse_endpoint_uri(endpoint),
        endpoint_mode=_parse_endpoint_mode(endpoint_mode),
        ec2_instance_profile_name=_validate_profile_name(instance_profile_name),
    )


def fetch_token(
    *,
    send: Callable[[HTTPRequest], Any],
    read_body: Callable[[Any], Any],
    config: IMDSConfig,
) -> Program[str]:
    """Request an IMDSv2 session token."""
    request = HTTPRequest(
        method="PUT",
        destination=_endpoint_path(config.endpoint_uri, _TOKEN_PATH),
        fields=Fields(
            [
                _USER_AGENT_FIELD,
                Field(
                    name="x-aws-ec2-metadata-token-ttl-seconds",
                    values=[str(config.token_ttl)],
                ),
            ]
        ),
    )
    response = yield lambda: send(request)
    body: bytes = yield lambda: read_body(response.body)
    if response.status != 200:
        raise SmithyIdentityError(
            f"IMDS returned {response.status} when fetching a metadata token."
        )
    return body.decode("utf-8")


def fetch_metadata(
    *,
    send: Callable[[HTTPRequest], Any],
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
            [_USER_AGENT_FIELD, Field(name="x-aws-ec2-metadata-token", values=[token])]
        ),
    )
    response = yield lambda: send(request)
    body: bytes = yield lambda: read_body(response.body)
    if response.status != 200:
        raise SmithyIdentityError(f"IMDS returned {response.status} for path '{path}'.")
    return body.decode("utf-8")


def resolve_credentials(
    *, get: Callable[[str], Any], instance_profile_name: str | None
) -> Program[AWSCredentialsIdentity]:
    """Resolve credentials for the configured or discovered instance profile."""
    profile = instance_profile_name
    if profile is None:
        profile = yield lambda: get(_METADATA_PATH_BASE)
    document: str = yield lambda: get(f"{_METADATA_PATH_BASE}/{profile}")
    return _parse_identity(json.loads(document))


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


def _validate_profile_name(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise IMDSConfigurationError(
            "The configured EC2 instance profile name must not be blank."
        )
    return value
