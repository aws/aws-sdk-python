# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import asyncio
import io
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aws_credentials_imds.aio.client import AsyncIMDSClient, AsyncIMDSTokenCache
from aws_credentials_imds.client import IMDSConfig, IMDSToken
from smithy_core.exceptions import RetryError, SmithyIdentityError
from smithy_core.retries import SimpleRetryStrategy
from smithy_http import Field, Fields
from smithy_http.aio import HTTPRequest


async def test_get_token_reuses_an_unexpired_token() -> None:
    http_client = AsyncMock()
    token_cache = AsyncIMDSTokenCache(http_client, MagicMock())
    token = IMDSToken("token", 100)
    token_cache._token = token

    assert await token_cache.get_token() is token
    http_client.send.assert_not_called()


async def test_get_token_replaces_an_expired_token() -> None:
    http_client = AsyncMock()
    http_client.send.return_value = Mock(status=200, body=b"new", fields=Fields())
    token_cache = AsyncIMDSTokenCache(http_client, IMDSConfig())
    expired = MagicMock()
    expired.is_expired.return_value = True
    token_cache._token = expired

    token = await token_cache.get_token()

    assert token.value == "new"
    assert token_cache._token is token


async def test_token_cache_refresh() -> None:
    # Test that AsyncIMDSTokenCache correctly refreshes the token when needed
    http_client = AsyncMock()
    config = MagicMock()
    config.token_ttl = 100
    config.timeout = 1.0
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.body = b"new-token-value"
    response_mock.fields = Fields()
    http_client.send.return_value = response_mock
    token_cache = AsyncIMDSTokenCache(http_client, config)
    assert token_cache._token is None
    await token_cache._refresh()
    assert token_cache._token is not None
    assert token_cache._token.value == "new-token-value"
    assert token_cache._token._ttl == 100


@pytest.mark.parametrize(
    ("header", "expected_ttl"),
    [
        ("30", 30),
        # An absent, malformed or non-positive TTL falls back to the requested one.
        (None, 100),
        ("soon", 100),
        ("0", 100),
        ("-5", 100),
    ],
)
async def test_token_ttl_comes_from_the_response(
    header: str | None, expected_ttl: int
) -> None:
    http_client = AsyncMock()
    http_client.send.return_value = _token(ttl=header)
    token_cache = AsyncIMDSTokenCache(http_client, IMDSConfig(token_ttl=100))

    token = await token_cache.get_token()

    assert token.value == "token"
    assert token._ttl == expected_ttl


async def test_token_cache_refresh_non_200() -> None:
    # A non-200 response must not be cached as the token value.
    http_client = AsyncMock()
    config = MagicMock()
    config.token_ttl = 100
    config.timeout = 1.0
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


def _response(status: int, body: bytes = b"", fields: Fields | None = None) -> Mock:
    return Mock(status=status, body=body, fields=fields or Fields())


def _token(status: int = 200, value: bytes = b"token", ttl: str | None = None) -> Mock:
    # IMDS sends its header names in mixed case.
    fields = Fields()
    if ttl is not None:
        fields.set_field(
            Field(name="X-aws-ec2-metadata-token-ttl-seconds", values=[ttl])
        )
    return _response(status, value, fields)


def _requests(http_client: AsyncMock) -> list[HTTPRequest]:
    return [call.kwargs["request"] for call in http_client.send.call_args_list]


async def _get(http_client: AsyncMock, config: IMDSConfig | None = None) -> str:
    # The retry tests pin three attempts rather than follow the default.
    client = AsyncIMDSClient(http_client, config or IMDSConfig(max_attempts=3))
    return await client.get(path="/test-path")


def _patch_sleep() -> Any:
    return patch(
        "aws_credentials_imds.aio.client.asyncio.sleep", new_callable=AsyncMock
    )


async def test_get_first_try_sends_token_put_then_get() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(200, b"metadata")]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET"]
    sleep.assert_not_awaited()


async def test_get_applies_default_read_timeout() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(200, b"metadata")]

    await _get(http_client)

    for call in http_client.send.call_args_list:
        assert call.kwargs["request_config"].read_timeout == 1.0


async def test_get_retries_server_error() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        _token(),
        _response(500),
        _response(200, b"metadata"),
    ]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET"]
    sleep.assert_awaited_once_with(0.25)


async def test_get_retries_token_server_error() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        _token(503),
        _token(),
        _response(200, b"metadata"),
    ]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "PUT", "GET"]
    assert sleep.await_count == 1


@pytest.mark.parametrize(
    "error", [ConnectionError("connection refused"), TimeoutError("timed out")]
)
async def test_get_retries_connection_errors_and_timeouts(error: Exception) -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), error, _response(200, b"metadata")]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    assert sleep.await_count == 1


async def test_get_retries_token_connection_error() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        ConnectionError("connection refused"),
        _token(),
        _response(200, b"metadata"),
    ]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    assert sleep.await_count == 1


async def test_get_401_fetches_new_token_before_retry() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        _token(value=b"token-1"),
        _response(401),
        _token(value=b"token-2"),
        _response(200, b"metadata"),
    ]

    with _patch_sleep() as sleep:
        assert await _get(http_client) == "metadata"

    requests = _requests(http_client)
    assert [r.method for r in requests] == ["PUT", "GET", "PUT", "GET"]
    assert requests[1].fields["x-aws-ec2-metadata-token"].values == ["token-1"]
    assert requests[3].fields["x-aws-ec2-metadata-token"].values == ["token-2"]
    assert sleep.await_count == 1


@pytest.mark.parametrize("status", [400, 403])
async def test_get_does_not_retry_token_client_errors(status: int) -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(status)]

    with _patch_sleep() as sleep:
        with pytest.raises(
            SmithyIdentityError, match=f"IMDS returned {status} when fetching"
        ):
            await _get(http_client)

    assert http_client.send.call_count == 1
    sleep.assert_not_awaited()


@pytest.mark.parametrize("status", [403, 404])
async def test_get_does_not_retry_metadata_client_errors(status: int) -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(status)]

    with _patch_sleep() as sleep:
        with pytest.raises(
            SmithyIdentityError,
            match=f"IMDS returned {status} for path '/test-path'",
        ):
            await _get(http_client)

    assert http_client.send.call_count == 2
    sleep.assert_not_awaited()


async def test_get_raises_after_max_attempts() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token()] + [_response(500)] * 3

    with _patch_sleep() as sleep:
        with pytest.raises(SmithyIdentityError, match=r"after 3 attempt\(s\)"):
            await _get(http_client)

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET", "GET"]
    assert [call.args[0] for call in sleep.await_args_list] == [0.25, 0.5]


async def test_get_honors_configured_max_attempts() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(500)]

    with _patch_sleep() as sleep:
        with pytest.raises(SmithyIdentityError, match=r"after 1 attempt\(s\)"):
            await _get(http_client, IMDSConfig(max_attempts=1))

    assert http_client.send.call_count == 1
    sleep.assert_not_awaited()


async def _hang(**kwargs: Any) -> Any:
    await asyncio.Event().wait()


async def _hang_body(body: Any) -> bytes:
    return await _hang()


async def test_get_times_out_a_hanging_send() -> None:
    # aiohttp ignores read_timeout, so the client must cut off a slow request itself.
    http_client = AsyncMock()
    http_client.send.side_effect = _hang

    with pytest.raises(SmithyIdentityError, match=r"after 1 attempt\(s\)") as exc:
        await _get(http_client, IMDSConfig(max_attempts=1, timeout=0.01))

    request_error = exc.value.__cause__
    assert request_error is not None
    assert isinstance(request_error.__cause__, TimeoutError)


async def test_get_times_out_a_hanging_body_read() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(200, b"metadata")]

    with patch(
        "aws_credentials_imds.aio.client.read_streaming_blob_async", new=_hang_body
    ):
        with pytest.raises(SmithyIdentityError) as exc:
            await _get(http_client, IMDSConfig(max_attempts=1, timeout=0.01))

    request_error = exc.value.__cause__
    assert request_error is not None
    assert isinstance(request_error.__cause__, TimeoutError)


async def test_get_does_not_retry_an_undecodable_body() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(200, b"\xff")]

    with pytest.raises(UnicodeDecodeError):
        await _get(http_client, IMDSConfig(max_attempts=3))

    assert http_client.send.await_count == 2


@pytest.mark.parametrize("status", [401, 404, 429])
async def test_get_retries_other_token_failures(status: int) -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        _token(status),
        _token(),
        _response(200, b"metadata"),
    ]

    with _patch_sleep():
        assert await _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "PUT", "GET"]


@pytest.mark.parametrize("status", [400, 405, 429])
async def test_get_retries_other_metadata_failures(status: int) -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        _token(),
        _response(status),
        _response(200, b"metadata"),
    ]

    with _patch_sleep():
        assert await _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET"]


async def test_get_token_survives_invalidation_after_its_check() -> None:
    # Another caller drops the token right after this one checked it's still valid.
    token_cache = AsyncIMDSTokenCache(AsyncMock(), IMDSConfig())

    class InvalidatedOnCheck(IMDSToken):
        def is_expired(self) -> bool:
            token_cache._invalidate(self)
            return False

    token = InvalidatedOnCheck("token", 100)
    token_cache._token = token

    assert await token_cache.get_token() is token


async def test_get_closes_a_body_whose_read_times_out() -> None:
    class StalledBody:
        closed = False

        async def read(self, size: int = -1) -> bytes:
            await asyncio.Event().wait()
            return b""

        async def close(self) -> None:
            self.closed = True

    body = StalledBody()
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), Mock(status=200, body=body)]

    with pytest.raises(SmithyIdentityError):
        await _get(http_client, IMDSConfig(max_attempts=1, timeout=0.01))

    assert body.closed


async def test_get_reads_a_body_with_a_synchronous_close() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [
        Mock(status=200, body=io.BytesIO(b"token"), fields=Fields()),
        Mock(status=200, body=io.BytesIO(b"metadata"), fields=Fields()),
    ]

    assert await _get(http_client, IMDSConfig(max_attempts=1)) == "metadata"


class _FixedBackoff:
    def compute_next_backoff_delay(self, retry_attempt: int) -> float:
        return 0.123


async def test_get_uses_a_custom_retry_strategy() -> None:
    strategy = Mock(
        wraps=SimpleRetryStrategy(backoff_strategy=_FixedBackoff(), max_attempts=2)
    )
    strategy.max_attempts = 2
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(500), _response(200, b"ok")]

    with _patch_sleep() as sleep:
        assert await _get(http_client, IMDSConfig(retry_strategy=strategy)) == "ok"

    strategy.refresh_retry_token_for_retry.assert_called_once()
    strategy.record_success.assert_called_once()
    sleep.assert_awaited_once_with(0.123)


async def test_get_reports_a_retry_strategy_refusal() -> None:
    strategy = Mock(wraps=SimpleRetryStrategy(max_attempts=5))
    strategy.max_attempts = 5
    strategy.refresh_retry_token_for_retry.side_effect = RetryError("quota spent")
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(500)]

    with pytest.raises(
        SmithyIdentityError,
        match=r"after 1 attempt\(s\): IMDS returned 500 .*\(quota spent\)",
    ):
        await _get(http_client, IMDSConfig(retry_strategy=strategy))

    strategy.record_success.assert_not_called()


async def test_get_raises_a_non_retryable_error_without_asking_the_strategy() -> None:
    strategy = Mock(wraps=SimpleRetryStrategy(max_attempts=5))
    strategy.max_attempts = 5
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(404)]

    with pytest.raises(SmithyIdentityError, match="returned 404"):
        await _get(http_client, IMDSConfig(retry_strategy=strategy))

    strategy.refresh_retry_token_for_retry.assert_not_called()


async def test_get_passes_config_timeout_as_read_timeout() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = [_token(), _response(200, b"ok")]

    await _get(http_client, IMDSConfig(timeout=2.5))

    for call in http_client.send.call_args_list:
        assert call.kwargs["request_config"].read_timeout == 2.5


async def test_asyncio_timeout_is_flagged_as_a_timeout() -> None:
    http_client = AsyncMock()
    http_client.send.side_effect = _hang

    with pytest.raises(SmithyIdentityError) as exc:
        await _get(http_client, IMDSConfig(max_attempts=1, timeout=0.01))

    assert getattr(exc.value.__cause__, "is_timeout_error") is True
