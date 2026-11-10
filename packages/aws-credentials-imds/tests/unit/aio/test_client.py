# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from unittest.mock import AsyncMock, MagicMock

import pytest
from aws_credentials_imds.aio.client import AsyncIMDSClient, AsyncIMDSTokenCache
from aws_credentials_imds.client import IMDSConfig, IMDSToken
from smithy_core.exceptions import SmithyIdentityError
from smithy_http.aio import HTTPRequest


async def test_token_cache_should_refresh() -> None:
    http_client = AsyncMock()
    config = MagicMock()
    # A new token cache needs a refresh
    token_cache = AsyncIMDSTokenCache(http_client, config)
    assert token_cache._should_refresh()
    # A token cache with an unexpired token doesn't need a refresh
    token_cache._token = MagicMock()
    token_cache._token.is_expired.return_value = False
    assert not token_cache._should_refresh()
    # A token cache with an expired token needs a refresh
    token_cache._token.is_expired.return_value = True
    assert token_cache._should_refresh()


async def test_token_cache_refresh() -> None:
    # Test that AsyncIMDSTokenCache correctly refreshes the token when needed
    http_client = AsyncMock()
    config = MagicMock()
    config.token_ttl = 100
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.body = b"new-token-value"
    http_client.send.return_value = response_mock
    token_cache = AsyncIMDSTokenCache(http_client, config)
    assert token_cache._should_refresh()
    await token_cache._refresh()
    assert token_cache._token is not None
    assert token_cache._token.value == "new-token-value"
    assert token_cache._token._ttl == 100


async def test_token_cache_refresh_non_200() -> None:
    # A non-200 response must not be cached as the token value.
    http_client = AsyncMock()
    config = MagicMock()
    config.token_ttl = 100
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = AsyncMock()
    response_mock.status = 401
    response_mock.body = b"Unauthorized"
    http_client.send.return_value = response_mock
    token_cache = AsyncIMDSTokenCache(http_client, config)
    with pytest.raises(SmithyIdentityError):
        await token_cache._refresh()
    assert token_cache._token is None


async def test_token_cache_get_token() -> None:
    # Test that AsyncIMDSTokenCache returns an existing token or refreshes if expired
    http_client = AsyncMock()
    config = MagicMock()
    token_cache = AsyncIMDSTokenCache(http_client, config)
    token_cache._refresh = AsyncMock()
    token_cache._token = MagicMock()
    token_cache._token.is_expired.return_value = False
    token = await token_cache.get_token()
    assert token == token_cache._token
    token_cache._refresh.assert_not_awaited()
    token_cache._token.is_expired.return_value = True
    await token_cache.get_token()
    token_cache._refresh.assert_awaited()


async def test_imds_client_get() -> None:
    # Test AsyncIMDSClient.get() method to retrieve metadata from IMDS
    http_client = AsyncMock()
    config = IMDSConfig()
    response = AsyncMock()
    response.status = 200
    response.body = b"metadata-response"
    http_client.send.return_value = response

    client = AsyncIMDSClient(http_client, config)
    client._token_cache.get_token = AsyncMock(
        return_value=IMDSToken("mocked-token", config.token_ttl)
    )

    result = await client.get(path="/test-path")
    assert result == "metadata-response"

    request = http_client.send.call_args.kwargs["request"]
    assert isinstance(request, HTTPRequest)
    assert request.destination.path == "/test-path"
    assert request.method == "GET"
    assert request.fields["x-aws-ec2-metadata-token"].values == ["mocked-token"]


async def test_imds_client_get_non_200() -> None:
    # A non-200 metadata response must raise instead of returning the body.
    http_client = AsyncMock()
    config = IMDSConfig()
    response = AsyncMock()
    response.status = 404
    response.body = b"Not Found"
    http_client.send.return_value = response

    client = AsyncIMDSClient(http_client, config)
    client._token_cache.get_token = AsyncMock(
        return_value=IMDSToken("mocked-token", config.token_ttl)
    )

    with pytest.raises(SmithyIdentityError):
        await client.get(path="/test-path")
