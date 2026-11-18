# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio
from contextlib import suppress
from inspect import isawaitable
from typing import Any

from smithy_core.aio.program import run_program_async
from smithy_core.aio.utils import read_streaming_blob_async
from smithy_http import HTTPRequest
from smithy_http.aio.interfaces import AsyncHTTPClient, HTTPResponse
from smithy_http.interfaces import HTTPRequestConfiguration

from .._imds import (
    TIMEOUT_SECONDS,
    IMDSConfig,
    IMDSToken,
    fetch_token,
    get_metadata,
)


class AsyncIMDSTokenCache:
    """Holds and refreshes the token used to fetch instance metadata."""

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig):
        self._http_client = http_client
        self._config = config
        self._refresh_lock = asyncio.Lock()
        self._token: IMDSToken | None = None

    async def get_token(self) -> IMDSToken:
        """Return the cached session token, refreshing it once it expires."""
        # Read the token once: another task may invalidate it at any point.
        token = self._token
        if token is None or token.is_expired():
            token = await self._refresh()
        return token

    def _invalidate(self, token: IMDSToken) -> None:
        # Leave a token another task already refreshed in place.
        if self._token is token:
            self._token = None

    async def _refresh(self) -> IMDSToken:
        async with self._refresh_lock:
            token = self._token
            if token is not None and not token.is_expired():
                return token
            token = await run_program_async(
                fetch_token(
                    send=lambda request, config: _send(
                        self._http_client, request, config
                    ),
                    read_body=_read_body,
                    config=self._config,
                )
            )
            self._token = token
            return token


class AsyncIMDSClient:
    """Minimal asynchronous IMDSv2 client."""

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig | None = None):
        self._http_client = http_client
        self._config = config or IMDSConfig()
        self._token_cache = AsyncIMDSTokenCache(
            http_client=self._http_client, config=self._config
        )

    async def get(self, *, path: str) -> str:
        """Fetch the instance metadata at ``path``."""
        return await run_program_async(
            get_metadata(
                send=lambda request, config: _send(self._http_client, request, config),
                read_body=_read_body,
                sleep=asyncio.sleep,
                get_token=self._token_cache.get_token,
                invalidate_token=self._token_cache._invalidate,
                config=self._config,
                path=path,
            )
        )


# Async clients such as aiohttp don't apply HTTPRequestConfiguration.read_timeout,
# so the IMDS timeout is enforced here for any client.
async def _send(
    http_client: AsyncHTTPClient,
    request: HTTPRequest,
    config: HTTPRequestConfiguration,
) -> HTTPResponse:
    async with asyncio.timeout(TIMEOUT_SECONDS):
        return await http_client.send(request=request, request_config=config)


async def _read_body(body: Any) -> bytes:
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            return await read_streaming_blob_async(body)
    finally:
        # Hand the connection back, or drop it if the read was cut short, so a
        # timed-out attempt doesn't hold a connection from the caller's pool.
        # A close failure must not replace the read's own result or error.
        close = getattr(body, "close", None)
        if close is not None:
            with suppress(Exception):
                result = close()
                if isawaitable(result):
                    await result
