#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from smithy_core.aio.utils import read_streaming_blob_async
from smithy_core.utils import read_streaming_blob
from smithy_http import HTTPResponse
from smithy_http.aio.testing import AsyncMockHTTPClient
from smithy_http.interfaces import HTTPRequest, HTTPRequestConfiguration
from smithy_http.testing import MockHTTPClient

_LIST_BUCKETS_RESPONSE = (
    b"<ListAllMyBucketsResult><Buckets/><Owner><ID>owner</ID></Owner>"
    b"</ListAllMyBucketsResult>"
)
_ECS_RESPONSE = (
    b'{"AccessKeyId": "ECS_AKID", "SecretAccessKey": "SECRET", "Token": "TOKEN",'
    b' "Expiration": "2999-01-01T00:00:00Z"}'
)
_IMDS_RESPONSE = (
    b'{"Code": "Success", "AccessKeyId": "IMDS_AKID", "SecretAccessKey": "SECRET",'
    b' "Token": "TOKEN", "Expiration": "2999-01-01T00:00:00Z"}'
)


class CredentialSourceTransport(MockHTTPClient):
    """Answers every credential source, and S3, with a recognizable access key."""

    def send(
        self,
        request: HTTPRequest,
        *,
        request_config: HTTPRequestConfiguration | None = None,
    ) -> HTTPResponse:
        body = read_streaming_blob(request.body)
        # Reading consumed the body, and the pipeline still sends this request.
        request.body = body
        self.add_response(*_answer(request, body))
        return super().send(request, request_config=request_config)


class AsyncCredentialSourceTransport(AsyncMockHTTPClient):
    """Answers every credential source, and S3, with a recognizable access key."""

    async def send(
        self,
        request: HTTPRequest,
        *,
        request_config: HTTPRequestConfiguration | None = None,
    ) -> HTTPResponse:
        body = await read_streaming_blob_async(request.body)
        # Reading consumed the body, and the pipeline still sends this request.
        request.body = body
        self.add_response(*_answer(request, body))
        return await super().send(request, request_config=request_config)


def signing_access_key(transport: MockHTTPClient | AsyncMockHTTPClient) -> str:
    """Return the access key the last request was signed with."""
    request = transport.captured_requests[-1]
    for field in request.fields:
        if field.name.lower() == "authorization":
            match = re.search(r"Credential=([^/]+)/", field.values[0])
            assert match is not None, field.values[0]
            return match.group(1)
    raise AssertionError("the last request wasn't signed")


def _answer(
    request: HTTPRequest, body: bytes
) -> tuple[int, list[tuple[str, str]], bytes]:
    host = request.destination.host
    path = request.destination.path or ""
    if host.startswith("sts."):
        form = parse_qs(body.decode())
        action = form["Action"][0]
        role_name = form["RoleArn"][0].rsplit("/", 1)[-1]
        # The action and role name tell apart the sources that call STS.
        return 200, [("content-type", "text/xml")], _sts_response(action, role_name)
    if host == "169.254.169.254":
        if request.method == "PUT":
            return 200, [], b"imds-session-token"
        if path.endswith("security-credentials/"):
            return 200, [], b"imds-role"
        return 200, [], _IMDS_RESPONSE
    if host == "127.0.0.1":
        return 200, [("content-type", "application/json")], _ECS_RESPONSE
    return 200, [("content-type", "application/xml")], _LIST_BUCKETS_RESPONSE


def _sts_response(action: str, role_name: str) -> bytes:
    return (
        f'<{action}Response xmlns="https://sts.amazonaws.com/doc/2011-06-15/">'
        f"<{action}Result><Credentials><AccessKeyId>{action}.{role_name}"
        "</AccessKeyId><SecretAccessKey>SECRET</SecretAccessKey>"
        "<SessionToken>TOKEN</SessionToken>"
        "<Expiration>2999-01-01T00:00:00Z</Expiration></Credentials>"
        f"</{action}Result></{action}Response>"
    ).encode()


@contextmanager
def fake_imds() -> Iterator[str]:
    """Serve IMDS credentials on 127.0.0.1 and yield its endpoint URL.

    The sync IMDS resolver uses its own HTTP client rather than the chain's, so
    a mock transport can't answer it.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeIMDSHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class _FakeIMDSHandler(BaseHTTPRequestHandler):
    def do_PUT(self) -> None:
        self._reply(b"imds-session-token")

    def do_GET(self) -> None:
        if self.path.rstrip("/").endswith("security-credentials"):
            self._reply(b"imds-role")
        else:
            self._reply(_IMDS_RESPONSE)

    def _reply(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass
