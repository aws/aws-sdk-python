# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio

from smithy_core.aio.program import run_program_async
from smithy_core.aio.utils import read_streaming_blob_async
from smithy_http.aio.interfaces import AsyncHTTPClient

from .._imds import IMDSConfig, IMDSToken, fetch_metadata, fetch_token


class AsyncIMDSTokenCache:
    """Holds and refreshes the token used to fetch instance metadata."""

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig):
        self._http_client = http_client
        self._config = config
        self._refresh_lock = asyncio.Lock()
        self._token: IMDSToken | None = None

    async def get_token(self) -> IMDSToken:
        if self._should_refresh():
            await self._refresh()
        assert self._token is not None  # noqa: S101
        return self._token

    def _should_refresh(self) -> bool:
        return self._token is None or self._token.is_expired()

    async def _refresh(self) -> None:
        async with self._refresh_lock:
            if not self._should_refresh():
                return
            value = await run_program_async(
                fetch_token(
                    send=lambda request: self._http_client.send(request=request),
                    read_body=read_streaming_blob_async,
                    config=self._config,
                )
            )
            self._token = IMDSToken(value, self._config.token_ttl)


class AsyncIMDSClient:
    """Minimal asynchronous IMDSv2 client."""

    def __init__(self, http_client: AsyncHTTPClient, config: IMDSConfig | None = None):
        self._http_client = http_client
        self._config = config or IMDSConfig()
        self._token_cache = AsyncIMDSTokenCache(
            http_client=self._http_client, config=self._config
        )

    async def get(self, *, path: str) -> str:
        token = await self._token_cache.get_token()
        return await run_program_async(
            fetch_metadata(
                send=lambda request: self._http_client.send(request=request),
                read_body=read_streaming_blob_async,
                config=self._config,
                token=token.value,
                path=path,
            )
        )
