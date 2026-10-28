# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from smithy_core import URI
from smithy_core.aio.interfaces.retries import AsyncRetryStrategy
from smithy_core.aio.retries import AsyncSimpleRetryStrategy
from smithy_core.exceptions import SmithyIdentityError
from smithy_http import Field, Fields
from smithy_http.aio import HTTPRequest
from smithy_http.aio.interfaces import AsyncHTTPClient

from .. import __version__
from ..client import IMDSConfigurationError, IMDSToken

_USER_AGENT_FIELD = Field(
    name="User-Agent",
    values=[f"aws-sdk-python-imds-client/{__version__}"],
)


@dataclass(init=False)
class IMDSConfig:
    """Configuration for IMDSClient."""

    _HOST_MAPPING = MappingProxyType(
        {"IPv4": "169.254.169.254", "IPv6": "[fd00:ec2::254]"}
    )
    _MIN_TTL = 5
    _MAX_TTL = 21600

    retry_strategy: AsyncRetryStrategy
    endpoint_uri: URI
    endpoint_mode: Literal["IPv4", "IPv6"]
    token_ttl: int

    def __init__(
        self,
        *,
        retry_strategy: AsyncRetryStrategy | None = None,
        endpoint_uri: URI | None = None,
        endpoint_mode: Literal["IPv4", "IPv6"] = "IPv4",
        token_ttl: int = _MAX_TTL,
        ec2_instance_profile_name: str | None = None,
    ):
        # TODO: Implement IMDS request retries.
        self.retry_strategy = retry_strategy or AsyncSimpleRetryStrategy(max_attempts=3)
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


class IMDSTokenCache:
    """Holds and refreshes the token used to fetch instance metadata."""

    _TOKEN_PATH = "/latest/api/token"  # noqa: S105

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig):
        self._http_client = http_client
        self._config = config
        self._base_uri = config.endpoint_uri
        self._refresh_lock = asyncio.Lock()
        self._token = None

    def _should_refresh(self) -> bool:
        return self._token is None or self._token.is_expired()

    async def _refresh(self) -> None:
        async with self._refresh_lock:
            if not self._should_refresh():
                return
            headers = Fields(
                [
                    _USER_AGENT_FIELD,
                    Field(
                        name="x-aws-ec2-metadata-token-ttl-seconds",
                        values=[str(self._config.token_ttl)],
                    ),
                ]
            )
            request = HTTPRequest(
                method="PUT",
                destination=URI(
                    scheme=self._base_uri.scheme,
                    host=self._base_uri.host,
                    port=self._base_uri.port,
                    path=self._TOKEN_PATH,
                ),
                fields=headers,
            )
            response = await self._http_client.send(request)
            token_value = await response.consume_body_async()
            if response.status != 200:
                raise SmithyIdentityError(
                    f"IMDS returned {response.status} when fetching a metadata token."
                )
            self._token = IMDSToken(token_value.decode("utf-8"), self._config.token_ttl)

    async def get_token(self) -> IMDSToken:
        if self._should_refresh():
            await self._refresh()
        assert self._token is not None  # noqa: S101
        return self._token


class IMDSClient:
    """Minimal asynchronous IMDSv2 client."""

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig | None = None):
        self._http_client = http_client
        self._config = config or IMDSConfig()
        self._token_cache = IMDSTokenCache(
            http_client=self._http_client, config=self._config
        )

    async def get(self, *, path: str) -> str:
        token = await self._token_cache.get_token()
        headers = Fields(
            [
                _USER_AGENT_FIELD,
                Field(
                    name="x-aws-ec2-metadata-token",
                    values=[token.value],
                ),
            ]
        )
        request = HTTPRequest(
            method="GET",
            destination=URI(
                scheme=self._config.endpoint_uri.scheme,
                host=self._config.endpoint_uri.host,
                port=self._config.endpoint_uri.port,
                path=path,
            ),
            fields=headers,
        )
        response = await self._http_client.send(request=request)
        body = await response.consume_body_async()
        if response.status != 200:
            raise SmithyIdentityError(
                f"IMDS returned {response.status} for path '{path}'."
            )
        return body.decode("utf-8")
