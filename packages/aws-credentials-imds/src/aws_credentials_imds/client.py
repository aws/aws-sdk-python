# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import threading
import time
from contextlib import suppress
from inspect import isawaitable
from typing import Any

from smithy_core.program import run_program
from smithy_core.utils import read_streaming_blob
from smithy_http.interfaces import HTTPClient

from ._imds import (
    IMDSConfig,
    IMDSConfigurationError,
    IMDSToken,
    fetch_token,
    get_metadata,
)

__all__ = (
    "IMDSClient",
    "IMDSConfig",
    "IMDSConfigurationError",
    "IMDSToken",
    "IMDSTokenCache",
)


class IMDSTokenCache:
    """Holds and refreshes the token used to fetch instance metadata."""

    def __init__(self, http_client: HTTPClient, config: IMDSConfig):
        self._http_client = http_client
        self._config = config
        # Held for a whole token fetch, so that concurrent callers fetch only once.
        self._refresh_lock = threading.Lock()
        # Held only to swap the token, so invalidation never waits on a fetch.
        self._token_lock = threading.Lock()
        self._token: IMDSToken | None = None

    def get_token(self) -> IMDSToken:
        """Return the cached session token, refreshing it once it expires."""
        # Read the token once: another thread may invalidate it at any point.
        token = self._token
        if token is None or token.is_expired():
            token = self._refresh()
        return token

    def _invalidate(self, token: IMDSToken) -> None:
        # Leave a token another thread already refreshed in place.
        with self._token_lock:
            if self._token is token:
                self._token = None

    def _refresh(self) -> IMDSToken:
        with self._refresh_lock:
            token = self._token
            if token is not None and not token.is_expired():
                return token
            token = run_program(
                fetch_token(
                    send=lambda request, config: self._http_client.send(
                        request=request, request_config=config
                    ),
                    read_body=_read_body,
                    config=self._config,
                )
            )
            with self._token_lock:
                self._token = token
            return token


class IMDSClient:
    """Minimal synchronous IMDSv2 client."""

    def __init__(self, http_client: HTTPClient, config: IMDSConfig | None = None):
        self._http_client = http_client
        self._config = config or IMDSConfig()
        self._token_cache = IMDSTokenCache(
            http_client=self._http_client, config=self._config
        )

    def get(self, *, path: str) -> str:
        """Fetch the instance metadata at ``path``."""
        return run_program(
            get_metadata(
                send=lambda request, config: self._http_client.send(
                    request=request, request_config=config
                ),
                read_body=_read_body,
                sleep=time.sleep,
                get_token=self._token_cache.get_token,
                invalidate_token=self._token_cache._invalidate,
                config=self._config,
                path=path,
            )
        )


def _read_body(body: Any) -> bytes:
    try:
        return read_streaming_blob(body)
    finally:
        _close_quietly(body)


def _close_quietly(body: Any) -> None:
    # Hand the connection back, or drop it if the read was cut short, so a failed
    # attempt doesn't hold a connection from the caller's pool. A close failure
    # must not replace the read's own result or error.
    close = getattr(body, "close", None)
    if close is None:
        return
    with suppress(Exception):
        result = close()
        if isawaitable(result):
            # An async body can't be closed here; don't leave a never-awaited
            # coroutine behind.
            getattr(result, "close", lambda: None)()
