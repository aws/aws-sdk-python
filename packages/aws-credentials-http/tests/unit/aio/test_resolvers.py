# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aws_credentials_http.aio import ContainerCredentialsResolver
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_core import URI
from smithy_core.exceptions import SmithyIdentityError

DEFAULT_RESPONSE_DATA = {
    "AccessKeyId": "akid123",
    "SecretAccessKey": "s3cr3t",
    "Token": "session_token",
}
ISO8601 = "%Y-%m-%dT%H:%M:%SZ"


def mock_http_client_response(status: int, body: bytes) -> AsyncMock:
    http_client = AsyncMock()
    response = AsyncMock()
    response.status = status
    response.consume_body_async.return_value = body
    http_client.send.return_value = response
    return http_client


def _assert_expected_identity(identity: AWSCredentialsIdentity) -> None:
    assert identity.access_key_id == DEFAULT_RESPONSE_DATA["AccessKeyId"]
    assert identity.secret_access_key == DEFAULT_RESPONSE_DATA["SecretAccessKey"]
    assert identity.session_token == DEFAULT_RESPONSE_DATA["Token"]


async def test_resolver_env_relative() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(
        os.environ, {ContainerCredentialsResolver.ENV_VAR: "/test"}, clear=True
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.2",
        path="/test",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    _assert_expected_identity(identity)


async def test_resolver_env_full() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(
        os.environ,
        {ContainerCredentialsResolver.ENV_VAR_FULL: "http://169.254.170.23/full"},
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.23",
        path="/full",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    assert http_request.destination.query is None
    _assert_expected_identity(identity)


async def test_resolver_env_full_with_query() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: (
                "http://169.254.170.23/full?role=task%2Fworker&version=1"
            )
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.23",
        path="/full",
        query="role=task%2Fworker&version=1",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    assert http_request.destination.query == "role=task%2Fworker&version=1"
    _assert_expected_identity(identity)


async def test_resolver_env_token() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN: "Bearer foobar",
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.23",
        path="/full",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    assert "Authorization" in http_request.fields
    auth_field = http_request.fields.get("Authorization")
    assert auth_field is not None
    assert auth_field.as_string() == "Bearer foobar"
    _assert_expected_identity(identity)


async def test_resolver_env_token_file(tmp_path: Path) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    token_file = tmp_path / "token_file"
    token_file.write_text("Bearer barfoo")

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN_FILE: str(token_file),
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.23",
        path="/full",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    assert "Authorization" in http_request.fields
    auth_field = http_request.fields.get("Authorization")
    assert auth_field is not None
    assert auth_field.as_string() == "Bearer barfoo"
    _assert_expected_identity(identity)


async def test_resolver_env_token_file_invalid_bytes(tmp_path: Path) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    token_file = tmp_path / "token_file"
    token_file.write_bytes(b"Bearer bar\xff\xfe\xfafoo")

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN_FILE: str(token_file),
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        with pytest.raises(
            SmithyIdentityError, match="Unable to read valid utf-8 bytes from "
        ):
            await resolver.get_identity(properties={})


async def test_resolver_env_token_file_precedence(tmp_path: Path) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    token_file = tmp_path / "token_file"
    token_file.write_text("Bearer barfoo")

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN_FILE: str(token_file),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN: "Bearer foobar",
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity = await resolver.get_identity(properties={})

    expected_url = URI(
        scheme="http",
        host="169.254.170.23",
        path="/full",
    )
    http_request = http_client.send.call_args_list[0].args[0]
    assert http_request.destination == expected_url
    assert "Authorization" in http_request.fields
    auth_field = http_request.fields.get("Authorization")
    assert auth_field is not None
    assert auth_field.as_string() == "Bearer barfoo"
    _assert_expected_identity(identity)


@pytest.mark.parametrize("token", ["Bearer foo\r\nInjected: bar", "Bearer foo\nbar"])
async def test_resolver_env_token_rejects_crlf(token: str) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN: token,
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        with pytest.raises(
            SmithyIdentityError, match="Auth token value is not a legal header value"
        ):
            await resolver.get_identity(properties={})

    http_client.send.assert_not_called()


async def test_resolver_env_token_file_rejects_crlf(tmp_path: Path) -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())
    token_file = tmp_path / "token_file"
    token_file.write_text("Bearer foo\r\nInjected: bar")

    with patch.dict(
        os.environ,
        {
            ContainerCredentialsResolver.ENV_VAR_FULL: ("http://169.254.170.23/full"),
            ContainerCredentialsResolver.ENV_VAR_AUTH_TOKEN_FILE: str(token_file),
        },
        clear=True,
    ):
        resolver = ContainerCredentialsResolver(http_client)
        with pytest.raises(
            SmithyIdentityError, match="Auth token value is not a legal header value"
        ):
            await resolver.get_identity(properties={})

    http_client.send.assert_not_called()


async def test_resolver_valid_credentials_reused() -> None:
    response_data = dict(DEFAULT_RESPONSE_DATA)
    expiration = datetime.now(UTC) + timedelta(minutes=10)
    response_data["Expiration"] = expiration.strftime(ISO8601)
    http_client = mock_http_client_response(200, json.dumps(response_data).encode())

    with patch.dict(
        os.environ, {ContainerCredentialsResolver.ENV_VAR: "/test"}, clear=True
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity_one = await resolver.get_identity(properties={})
        identity_two = await resolver.get_identity(properties={})

    _assert_expected_identity(identity_one)
    assert identity_one is identity_two


async def test_resolver_expired_credentials_refreshed() -> None:
    response_data = dict(DEFAULT_RESPONSE_DATA)
    expiration = datetime.now(UTC) - timedelta(minutes=10)
    response_data["Expiration"] = expiration.strftime(ISO8601)
    http_client = mock_http_client_response(200, json.dumps(response_data).encode())

    with patch.dict(
        os.environ, {ContainerCredentialsResolver.ENV_VAR: "/test"}, clear=True
    ):
        resolver = ContainerCredentialsResolver(http_client)
        identity_one = await resolver.get_identity(properties={})
        identity_two = await resolver.get_identity(properties={})

    _assert_expected_identity(identity_one)
    assert identity_one.access_key_id == identity_two.access_key_id
    assert identity_one.secret_access_key == identity_two.secret_access_key
    assert identity_one.session_token == identity_two.session_token
    assert identity_one is not identity_two


async def test_resolver_missing_env() -> None:
    response_body = json.dumps(DEFAULT_RESPONSE_DATA)
    http_client = mock_http_client_response(200, response_body.encode())

    with patch.dict(os.environ, {}, clear=True):
        resolver = ContainerCredentialsResolver(http_client)
        with pytest.raises(SmithyIdentityError):
            await resolver.get_identity(properties={})
