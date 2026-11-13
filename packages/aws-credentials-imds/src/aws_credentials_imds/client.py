# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import threading

from smithy_core.program import run_program
from smithy_core.utils import read_streaming_blob
from smithy_http.interfaces import HTTPClient

from ._imds import (
    IMDSConfig,
    IMDSConfigurationError,
    IMDSToken,
    fetch_metadata,
    fetch_token,
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
        self._refresh_lock = threading.Lock()
        self._token: IMDSToken | None = None

    def get_token(self) -> IMDSToken:
        """Return the cached session token, refreshing it once it expires."""
        if self._should_refresh():
            self._refresh()
        assert self._token is not None  # noqa: S101
        return self._token

    def _should_refresh(self) -> bool:
        return self._token is None or self._token.is_expired()

    def _refresh(self) -> None:
        with self._refresh_lock:
            if not self._should_refresh():
                return
            value = run_program(
                fetch_token(
                    send=lambda request: self._http_client.send(request=request),
                    read_body=read_streaming_blob,
                    config=self._config,
                )
            )
            self._token = IMDSToken(value, self._config.token_ttl)


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
        token = self._token_cache.get_token()
        return run_program(
            fetch_metadata(
                send=lambda request: self._http_client.send(request=request),
                read_body=read_streaming_blob,
                config=self._config,
                token=token.value,
                path=path,
            )
        )
