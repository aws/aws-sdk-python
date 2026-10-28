# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from unittest.mock import AsyncMock, MagicMock

import pytest
from aws_credentials_imds.aio.client import (
    IMDSClient,
    IMDSConfig,
    IMDSTokenCache,
)
from aws_credentials_imds.client import IMDSConfigurationError, IMDSToken
from smithy_core import URI
from smithy_core.aio.retries import AsyncSimpleRetryStrategy
from smithy_core.exceptions import SmithyIdentityError
from smithy_http.aio import HTTPRequest


def test_config_defaults() -> None:
    config = IMDSConfig()
    assert isinstance(config.retry_strategy, AsyncSimpleRetryStrategy)
    assert config.endpoint_uri == URI(
        scheme="http", host=IMDSConfig._HOST_MAPPING["IPv4"], port=80
    )
    assert config.endpoint_mode == "IPv4"
    assert config.token_ttl == 21600


def test_endpoint_resolution() -> None:
    config_ipv4 = IMDSConfig(endpoint_mode="IPv4")
    config_ipv6 = IMDSConfig(endpoint_mode="IPv6")
    assert config_ipv4.endpoint_uri.host == IMDSConfig._HOST_MAPPING["IPv4"]
    assert config_ipv6.endpoint_uri.host == IMDSConfig._HOST_MAPPING["IPv6"]


def test_config_uses_custom_endpoint() -> None:
    # The custom endpoint should take precedence over IPv4 endpoint resolution.
    config = IMDSConfig(
        endpoint_uri=URI(scheme="https", host="test.host", port=123),
        endpoint_mode="IPv4",
    )
    assert config.endpoint_uri == URI(scheme="https", host="test.host", port=123)

    # The custom endpoint takes precedence over IPv6 endpoint resolution.
    config = IMDSConfig(
        endpoint_uri=URI(scheme="https", host="test.host", port=123),
        endpoint_mode="IPv6",
    )
    assert config.endpoint_uri == URI(scheme="https", host="test.host", port=123)


def test_config_ttl_validation() -> None:
    # TTL values < _MIN_TTL should raise a configuration error
    with pytest.raises(IMDSConfigurationError):
        IMDSConfig(token_ttl=IMDSConfig._MIN_TTL - 1)
    # TTL values > _MAX_TTL should raise a configuration error
    with pytest.raises(IMDSConfigurationError):
        IMDSConfig(token_ttl=IMDSConfig._MAX_TTL + 1)


async def test_token_cache_should_refresh() -> None:
    http_client = AsyncMock()
    config = MagicMock()
    # A new token cache needs a refresh
    token_cache = IMDSTokenCache(http_client, config)
    assert token_cache._should_refresh()
    # A token cache with an unexpired token doesn't need a refresh
    token_cache._token = MagicMock()
    token_cache._token.is_expired.return_value = False
    assert not token_cache._should_refresh()
    # A token cache with an expired token needs a refresh
    token_cache._token.is_expired.return_value = True
    assert token_cache._should_refresh()


async def test_token_cache_refresh() -> None:
    # Test that IMDSTokenCache correctly refreshes the token when needed
    http_client = AsyncMock()
    config = MagicMock()
    config.token_ttl = 100
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.consume_body_async.return_value = b"new-token-value"
    http_client.send.return_value = response_mock
    token_cache = IMDSTokenCache(http_client, config)
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
    response_mock.consume_body_async.return_value = b"Unauthorized"
    http_client.send.return_value = response_mock
    token_cache = IMDSTokenCache(http_client, config)
    with pytest.raises(SmithyIdentityError):
        await token_cache._refresh()
    assert token_cache._token is None


async def test_token_cache_get_token() -> None:
    # Test that IMDSTokenCache returns an existing token or refreshes if expired
    http_client = AsyncMock()
    config = MagicMock()
    token_cache = IMDSTokenCache(http_client, config)
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
    # Test IMDSClient.get() method to retrieve metadata from IMDS
    http_client = AsyncMock()
    config = IMDSConfig()
    response = AsyncMock()
    response.status = 200
    response.consume_body_async.return_value = b"metadata-response"
    http_client.send.return_value = response

    client = IMDSClient(http_client, config)
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
    response.consume_body_async.return_value = b"Not Found"
    http_client.send.return_value = response

    client = IMDSClient(http_client, config)
    client._token_cache.get_token = AsyncMock(
        return_value=IMDSToken("mocked-token", config.token_ttl)
    )

    with pytest.raises(SmithyIdentityError):
        await client.get(path="/test-path")
