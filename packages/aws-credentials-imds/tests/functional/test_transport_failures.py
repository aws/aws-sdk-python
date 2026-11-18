# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Real HTTP clients against a fake IMDS on loopback that fails at the socket level.

Mocked HTTP clients can't show which exceptions urllib3 and aiohttp actually raise,
so these tests check that every such failure is retried.
"""

import socket
import struct
import threading
from collections.abc import Iterator
from typing import Literal

import pytest
from aws_credentials_imds import IMDSConfig
from aws_credentials_imds.aio.client import AsyncIMDSClient
from aws_credentials_imds.client import IMDSClient
from smithy_core import URI
from smithy_core.exceptions import SmithyIdentityError
from smithy_http.aio.aiohttp import AIOHTTPClient
from smithy_http.urllib3 import Urllib3HTTPClient, Urllib3HTTPClientConfig

type Failure = Literal["refused", "close", "reset", "silent"]

_FAILURES: list[Failure] = ["refused", "close", "reset", "silent"]
_ATTEMPTS = 2


class _FailingServer:
    """Accepts connections on 127.0.0.1 and fails each one the same way."""

    def __init__(self, failure: Failure):
        self.failure = failure
        self.accepted = 0
        self._sock = socket.create_server(("127.0.0.1", 0))
        self._sock.settimeout(0.1)
        self.port: int = self._sock.getsockname()[1]
        self._held: list[socket.socket] = []
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        if failure == "refused":
            # Nothing listens on the port, so connections are refused.
            self._sock.close()
        else:
            self._thread.start()

    def _serve(self) -> None:
        while not self._stopped.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            self.accepted += 1
            conn.settimeout(0.5)
            try:
                conn.recv(65536)
            except OSError:
                pass
            if self.failure == "close":
                conn.close()
            elif self.failure == "reset":
                # Linger with a zero timeout makes close() send an RST.
                conn.setsockopt(
                    socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
                )
                conn.close()
            else:
                self._held.append(conn)

    def close(self) -> None:
        self._stopped.set()
        if self._thread.is_alive():
            self._thread.join()
        for conn in self._held:
            conn.close()
        self._sock.close()

    def config(self) -> IMDSConfig:
        return IMDSConfig(
            max_attempts=_ATTEMPTS,
            endpoint_uri=URI(scheme="http", host="127.0.0.1", port=self.port),
        )


@pytest.fixture(params=_FAILURES)
def server(request: pytest.FixtureRequest) -> Iterator[_FailingServer]:
    failing = _FailingServer(request.param)
    yield failing
    failing.close()


def _assert_retried(error: SmithyIdentityError, server: _FailingServer) -> None:
    assert f"after {_ATTEMPTS} attempt(s)" in str(error)
    # Each attempt fails on its token request, which opens a connection. aiohttp
    # resends an idempotent request once itself when the server drops it.
    if server.failure != "refused":
        assert server.accepted >= _ATTEMPTS


def test_sync_client_retries_socket_failures(server: _FailingServer) -> None:
    http_client = Urllib3HTTPClient(
        client_config=Urllib3HTTPClientConfig(connect_timeout=1.0, read_timeout=1.0)
    )
    with http_client:
        client = IMDSClient(http_client=http_client, config=server.config())
        with pytest.raises(SmithyIdentityError) as exc:
            client.get(path="/latest/meta-data/iam/security-credentials")
    _assert_retried(exc.value, server)


async def test_async_client_retries_socket_failures(server: _FailingServer) -> None:
    async with AIOHTTPClient() as http_client:
        client = AsyncIMDSClient(http_client=http_client, config=server.config())
        with pytest.raises(SmithyIdentityError) as exc:
            await client.get(path="/latest/meta-data/iam/security-credentials")
    _assert_retried(exc.value, server)
