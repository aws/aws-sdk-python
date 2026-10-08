# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
from unittest.mock import AsyncMock, patch

import pytest
from aws_credentials_http.client import HttpCredentialsClient
from smithy_core import URI
from smithy_core.exceptions import SmithyIdentityError
from smithy_http import Fields

DEFAULT_RESPONSE_DATA = {
    "AccessKeyId": "akid123",
    "SecretAccessKey": "s3cr3t",
    "Token": "session_token",
}


def mock_http_client_response(status: int, body: bytes) -> AsyncMock:
    http_client = AsyncMock()
    response = AsyncMock()
    response.status = status
    response.consume_body_async.return_value = body
    http_client.send.return_value = response
    return http_client


def _assert_expected_credentials(
    credentials: dict[str, str],
    access_key_id: str,
    secret_access_key: str,
    token: str,
) -> None:
    assert credentials["AccessKeyId"] == access_key_id
    assert credentials["SecretAccessKey"] == secret_access_key
    assert credentials["Token"] == token


@pytest.mark.parametrize(
    "host",
    ["169.254.170.2", "169.254.170.23", "fd00:ec2::23", "localhost", "127.0.0.2"],
)
async def test_client_valid_host(host: str) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    client = HttpCredentialsClient(http_client)

    credentials = await client.get_credentials(URI(scheme="http", host=host), Fields())

    _assert_expected_credentials(credentials, "akid123", "s3cr3t", "session_token")


async def test_client_https_host() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    client = HttpCredentialsClient(http_client)

    credentials = await client.get_credentials(
        URI(scheme="https", host="example.com"), Fields()
    )

    _assert_expected_credentials(credentials, "akid123", "s3cr3t", "session_token")


async def test_client_invalid_host() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    client = HttpCredentialsClient(http_client, retries=0)

    with pytest.raises(SmithyIdentityError):
        await client.get_credentials(
            URI(scheme="http", host="169.254.169.254"), Fields()
        )


async def test_client_non_200_response() -> None:
    http_client = mock_http_client_response(404, b"not found")
    client = HttpCredentialsClient(http_client, retries=1)

    with pytest.raises(SmithyIdentityError) as exc_info:
        await client.get_credentials(URI(scheme="http", host="169.254.170.2"), Fields())

    assert "Container metadata service returned 404" in str(exc_info.value.__cause__)
    assert "Failed to retrieve container metadata after 1 attempt(s)" in str(
        exc_info.value
    )


async def test_client_invalid_json() -> None:
    http_client = mock_http_client_response(
        200, b"<!DOCTYPE html><head><title>proxy</title>"
    )
    client = HttpCredentialsClient(http_client, retries=1)

    with pytest.raises(SmithyIdentityError):
        await client.get_credentials(URI(scheme="http", host="169.254.170.2"), Fields())


async def test_client_applies_read_timeout() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    client = HttpCredentialsClient(http_client, timeout=5)

    await client.get_credentials(URI(scheme="http", host="169.254.170.2"), Fields())

    _, kwargs = http_client.send.call_args
    assert kwargs["request_config"].read_timeout == 5


async def test_client_retries() -> None:
    http_client = AsyncMock()
    client = HttpCredentialsClient(http_client, retries=2)
    uri = URI(scheme="http", host="169.254.170.2", path="/task")
    http_client.send.side_effect = Exception()

    with patch(
        "aws_credentials_http.client.asyncio.sleep", new_callable=AsyncMock
    ) as sleep:
        with pytest.raises(SmithyIdentityError):
            await client.get_credentials(uri, Fields())

    assert http_client.send.call_count == 2
    assert sleep.await_count == 1
