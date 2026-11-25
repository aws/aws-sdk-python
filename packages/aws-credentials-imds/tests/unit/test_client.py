# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import io
import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from aws_credentials_imds._imds import _BACKOFF, get_metadata
from aws_credentials_imds.client import (
    IMDSClient,
    IMDSConfig,
    IMDSConfigurationError,
    IMDSToken,
    IMDSTokenCache,
)
from smithy_core import URI
from smithy_core.exceptions import ClientTimeoutError, RetryError, SmithyIdentityError
from smithy_core.program import run_program
from smithy_core.retries import SimpleRetryStrategy
from smithy_http import Field, Fields, HTTPRequest


def test_config_defaults() -> None:
    config = IMDSConfig()
    assert config.max_attempts == 4
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


def test_token_creation() -> None:
    token = IMDSToken(value="test-token", ttl=100)
    assert token._value == "test-token"
    assert token._ttl == 100
    assert not token.is_expired()


def test_token_expiration() -> None:
    token = IMDSToken(value="test-token", ttl=1)
    assert not token.is_expired()
    time.sleep(1.1)
    assert token.is_expired()


def test_get_token_reuses_an_unexpired_token() -> None:
    http_client = Mock()
    token_cache = IMDSTokenCache(http_client, MagicMock())
    token = IMDSToken("token", 100)
    token_cache._token = token

    assert token_cache.get_token() is token
    http_client.send.assert_not_called()


def test_get_token_replaces_an_expired_token() -> None:
    http_client = Mock()
    http_client.send.return_value = Mock(status=200, body=b"new", fields=Fields())
    token_cache = IMDSTokenCache(http_client, IMDSConfig())
    expired = MagicMock()
    expired.is_expired.return_value = True
    token_cache._token = expired

    token = token_cache.get_token()

    assert token.value == "new"
    assert token_cache._token is token


def test_token_cache_refresh() -> None:
    # Test that IMDSTokenCache correctly refreshes the token when needed
    http_client = Mock()
    config = MagicMock()
    config.token_ttl = 100
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = Mock()
    response_mock.status = 200
    response_mock.body = b"new-token-value"
    response_mock.fields = Fields()
    http_client.send.return_value = response_mock
    token_cache = IMDSTokenCache(http_client, config)
    assert token_cache._token is None
    token_cache._refresh()
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
def test_token_ttl_comes_from_the_response(
    header: str | None, expected_ttl: int
) -> None:
    http_client = Mock()
    http_client.send.return_value = _token(ttl=header)
    token_cache = IMDSTokenCache(http_client, IMDSConfig(token_ttl=100))

    token = token_cache.get_token()

    assert token.value == "token"
    assert token._ttl == expected_ttl


def test_token_cache_refresh_non_200() -> None:
    # A non-200 response must not be cached as the token value.
    http_client = Mock()
    config = MagicMock()
    config.token_ttl = 100
    config.endpoint_uri.scheme = "http"
    config.endpoint_uri.host = "169.254.169.254"
    response_mock = Mock()
    response_mock.status = 401
    response_mock.body = b"Unauthorized"
    http_client.send.return_value = response_mock
    token_cache = IMDSTokenCache(http_client, config)
    with pytest.raises(SmithyIdentityError):
        token_cache._refresh()
    assert token_cache._token is None


def test_token_cache_get_token() -> None:
    # Test that IMDSTokenCache returns an existing token or refreshes if expired
    http_client = Mock()
    config = MagicMock()
    token_cache = IMDSTokenCache(http_client, config)
    token_cache._refresh = Mock()
    token_cache._token = MagicMock()
    token_cache._token.is_expired.return_value = False
    token = token_cache.get_token()
    assert token == token_cache._token
    token_cache._refresh.assert_not_called()
    token_cache._token.is_expired.return_value = True
    token_cache.get_token()
    token_cache._refresh.assert_called()


def test_imds_client_get() -> None:
    # Test IMDSClient.get() method to retrieve metadata from IMDS
    http_client = Mock()
    config = IMDSConfig()
    response = Mock()
    response.status = 200
    response.body = b"metadata-response"
    http_client.send.return_value = response

    client = IMDSClient(http_client, config)
    client._token_cache.get_token = Mock(
        return_value=IMDSToken("mocked-token", config.token_ttl)
    )

    result = client.get(path="/test-path")
    assert result == "metadata-response"

    request = http_client.send.call_args.kwargs["request"]
    assert isinstance(request, HTTPRequest)
    assert request.destination.path == "/test-path"
    assert request.method == "GET"
    assert request.fields["x-aws-ec2-metadata-token"].values == ["mocked-token"]


def test_imds_client_get_non_200() -> None:
    # A non-200 metadata response must raise instead of returning the body.
    http_client = Mock()
    config = IMDSConfig()
    response = Mock()
    response.status = 404
    response.body = b"Not Found"
    http_client.send.return_value = response

    client = IMDSClient(http_client, config)
    client._token_cache.get_token = Mock(
        return_value=IMDSToken("mocked-token", config.token_ttl)
    )

    with pytest.raises(SmithyIdentityError):
        client.get(path="/test-path")


def test_config_max_attempts() -> None:
    assert IMDSConfig(max_attempts=1).max_attempts == 1
    assert IMDSConfig(max_attempts=5).max_attempts == 5


@pytest.mark.parametrize("value", [0, -1, True, "3", 2.0])
def test_config_rejects_invalid_max_attempts(value: Any) -> None:
    with pytest.raises(IMDSConfigurationError, match="max attempts"):
        IMDSConfig(max_attempts=value)


def test_config_default_retry_strategy() -> None:
    strategy = IMDSConfig(max_attempts=3).retry_strategy
    assert isinstance(strategy, SimpleRetryStrategy)
    assert strategy.max_attempts == 3
    assert strategy.backoff_strategy is _BACKOFF


def test_config_retry_strategy_overrides_max_attempts() -> None:
    strategy = SimpleRetryStrategy(max_attempts=2)
    config = IMDSConfig(max_attempts=5, retry_strategy=strategy)
    assert config.retry_strategy is strategy
    assert config.max_attempts == 2


def test_config_retry_strategy_skips_max_attempts_validation() -> None:
    # max_attempts is ignored when a strategy is given, so it isn't validated.
    strategy = SimpleRetryStrategy(max_attempts=2)
    assert IMDSConfig(max_attempts=0, retry_strategy=strategy).max_attempts == 2


def test_config_timeout() -> None:
    assert IMDSConfig().timeout == 1.0
    assert IMDSConfig(timeout=2).timeout == 2.0
    assert IMDSConfig(timeout=0.5).timeout == 0.5


@pytest.mark.parametrize("value", [0, -1, True, "1", float("nan"), float("inf"), None])
def test_config_rejects_invalid_timeout(value: Any) -> None:
    with pytest.raises(IMDSConfigurationError, match="timeout"):
        IMDSConfig(timeout=value)


def test_backoff_is_exponential_and_capped() -> None:
    assert [_BACKOFF.compute_next_backoff_delay(n) for n in range(1, 8)] == [
        0.25,
        0.5,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    ]


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


def _requests(http_client: Mock) -> list[HTTPRequest]:
    return [call.kwargs["request"] for call in http_client.send.call_args_list]


def _get(http_client: Mock, config: IMDSConfig | None = None) -> str:
    # The retry tests pin three attempts rather than follow the default.
    client = IMDSClient(http_client, config or IMDSConfig(max_attempts=3))
    return client.get(path="/test-path")


def test_program_sleeps_between_attempts_only() -> None:
    sleeps: list[float] = []
    token = IMDSToken("token", 100)
    sends: list[HTTPRequest] = []

    def send(request: HTTPRequest, config: Any) -> Mock:
        sends.append(request)
        return _response(500)

    with pytest.raises(SmithyIdentityError, match=r"after 6 attempt\(s\)"):
        run_program(
            get_metadata(
                send=send,
                read_body=lambda body: body,
                sleep=sleeps.append,
                get_token=lambda: token,
                invalidate_token=lambda _: None,
                config=IMDSConfig(max_attempts=6),
                path="/test-path",
            )
        )
    assert len(sends) == 6
    assert sleeps == [0.25, 0.5, 1.0, 1.0, 1.0]


def test_get_first_try_sends_token_put_then_get() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(200, b"metadata")]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET"]
    sleep.assert_not_called()


def test_get_applies_default_read_timeout() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(200, b"metadata")]

    _get(http_client)

    for call in http_client.send.call_args_list:
        assert call.kwargs["request_config"].read_timeout == 1.0


def test_get_retries_server_error() -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        _token(),
        _response(500),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    # The cached token is reused, so the retry is a single GET.
    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET"]
    sleep.assert_called_once_with(0.25)


def test_get_retries_token_server_error() -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        _token(503),
        _token(),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "PUT", "GET"]
    assert sleep.call_count == 1


@pytest.mark.parametrize(
    "error", [ConnectionError("connection refused"), TimeoutError("timed out")]
)
def test_get_retries_connection_errors_and_timeouts(error: Exception) -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), error, _response(200, b"metadata")]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    assert sleep.call_count == 1


def test_get_retries_token_connection_error() -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        ConnectionError("connection refused"),
        _token(),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    assert sleep.call_count == 1


def test_get_401_fetches_new_token_before_retry() -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        _token(value=b"token-1"),
        _response(401),
        _token(value=b"token-2"),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client) == "metadata"

    requests = _requests(http_client)
    assert [r.method for r in requests] == ["PUT", "GET", "PUT", "GET"]
    assert requests[1].fields["x-aws-ec2-metadata-token"].values == ["token-1"]
    assert requests[3].fields["x-aws-ec2-metadata-token"].values == ["token-2"]
    assert sleep.call_count == 1


@pytest.mark.parametrize("status", [400, 403])
def test_get_does_not_retry_token_client_errors(status: int) -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(status)]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        with pytest.raises(
            SmithyIdentityError, match=f"IMDS returned {status} when fetching"
        ):
            _get(http_client)

    assert http_client.send.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize("status", [403, 404])
def test_get_does_not_retry_metadata_client_errors(status: int) -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(status)]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        with pytest.raises(
            SmithyIdentityError,
            match=f"IMDS returned {status} for path '/test-path'",
        ):
            _get(http_client)

    assert http_client.send.call_count == 2
    sleep.assert_not_called()


def test_get_raises_after_max_attempts() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token()] + [_response(500)] * 3

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        with pytest.raises(SmithyIdentityError, match=r"after 3 attempt\(s\)"):
            _get(http_client)

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET", "GET"]
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]


def test_get_honors_configured_max_attempts() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(500)]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        with pytest.raises(SmithyIdentityError, match=r"after 1 attempt\(s\)"):
            _get(http_client, IMDSConfig(max_attempts=1))

    assert http_client.send.call_count == 1
    sleep.assert_not_called()


def test_get_retries_any_send_failure() -> None:
    # Any failed request is retried, whatever the HTTP client raised.
    class TransportError(Exception):
        pass

    http_client = Mock()
    http_client.send.side_effect = [
        _token(),
        TransportError("connection dropped"),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client, IMDSConfig(max_attempts=2)) == "metadata"

    sleep.assert_called_once_with(0.25)


def test_get_does_not_retry_an_undecodable_body() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(200, b"\xff")]

    with pytest.raises(UnicodeDecodeError):
        _get(http_client, IMDSConfig(max_attempts=3))

    assert http_client.send.call_count == 2


def test_default_is_three_retries() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token()] + [_response(500)] * 4

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        with pytest.raises(SmithyIdentityError, match=r"after 4 attempt\(s\)"):
            _get(http_client, IMDSConfig())

    assert http_client.send.call_count == 5
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5, 1.0]


@pytest.mark.parametrize("status", [401, 404, 429])
def test_get_retries_other_token_failures(status: int) -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        _token(status),
        _token(),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep"):
        assert _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "PUT", "GET"]


@pytest.mark.parametrize("status", [400, 405, 429])
def test_get_retries_other_metadata_failures(status: int) -> None:
    http_client = Mock()
    http_client.send.side_effect = [
        _token(),
        _response(status),
        _response(200, b"metadata"),
    ]

    with patch("aws_credentials_imds.client.time.sleep"):
        assert _get(http_client) == "metadata"

    assert [r.method for r in _requests(http_client)] == ["PUT", "GET", "GET"]


def test_get_token_survives_invalidation_after_its_check() -> None:
    # Another caller drops the token right after this one checked it's still valid.
    token_cache = IMDSTokenCache(Mock(), IMDSConfig())

    class InvalidatedOnCheck(IMDSToken):
        def is_expired(self) -> bool:
            token_cache._invalidate(self)
            return False

    token = InvalidatedOnCheck("token", 100)
    token_cache._token = token

    assert token_cache.get_token() is token


def test_get_closes_a_body_whose_read_fails() -> None:
    class FailingBody:
        closed = False

        def read(self, size: int = -1) -> bytes:
            raise TimeoutError("read timed out")

        def close(self) -> None:
            self.closed = True

    body = FailingBody()
    http_client = Mock()
    http_client.send.side_effect = [_token(), Mock(status=200, body=body)]

    with pytest.raises(SmithyIdentityError):
        _get(http_client, IMDSConfig(max_attempts=1))

    assert body.closed


def test_get_ignores_a_failing_close_after_a_good_read() -> None:
    class BadCloseBody(io.BytesIO):
        def close(self) -> None:
            raise OSError("close failed")

    http_client = Mock()
    http_client.send.side_effect = [
        Mock(status=200, body=BadCloseBody(b"token"), fields=Fields()),
        Mock(status=200, body=BadCloseBody(b"metadata"), fields=Fields()),
    ]

    assert _get(http_client, IMDSConfig(max_attempts=1)) == "metadata"


class _FixedBackoff:
    def compute_next_backoff_delay(self, retry_attempt: int) -> float:
        return 0.123


def test_get_uses_a_custom_retry_strategy() -> None:
    strategy = Mock(
        wraps=SimpleRetryStrategy(backoff_strategy=_FixedBackoff(), max_attempts=2)
    )
    strategy.max_attempts = 2
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(500), _response(200, b"ok")]

    with patch("aws_credentials_imds.client.time.sleep") as sleep:
        assert _get(http_client, IMDSConfig(retry_strategy=strategy)) == "ok"

    strategy.acquire_initial_retry_token.assert_called_once()
    strategy.refresh_retry_token_for_retry.assert_called_once()
    strategy.record_success.assert_called_once()
    # The strategy's backoff, not the IMDS default.
    sleep.assert_called_once_with(0.123)


def test_get_reports_a_retry_strategy_refusal() -> None:
    # A strategy can refuse a retry-safe error, for example when its quota is spent.
    strategy = Mock(wraps=SimpleRetryStrategy(max_attempts=5))
    strategy.max_attempts = 5
    strategy.refresh_retry_token_for_retry.side_effect = RetryError("quota spent")
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(500)]

    with pytest.raises(
        SmithyIdentityError,
        match=r"after 1 attempt\(s\): IMDS returned 500 .*\(quota spent\)",
    ) as exc:
        _get(http_client, IMDSConfig(retry_strategy=strategy))

    assert isinstance(exc.value.__cause__, SmithyIdentityError)
    strategy.record_success.assert_not_called()


def test_get_raises_a_non_retryable_error_without_asking_the_strategy() -> None:
    strategy = Mock(wraps=SimpleRetryStrategy(max_attempts=5))
    strategy.max_attempts = 5
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(404)]

    with pytest.raises(SmithyIdentityError, match="returned 404"):
        _get(http_client, IMDSConfig(retry_strategy=strategy))

    strategy.refresh_retry_token_for_retry.assert_not_called()


def test_get_passes_config_timeout_as_read_timeout() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(200, b"ok")]

    _get(http_client, IMDSConfig(timeout=2.5))

    for call in http_client.send.call_args_list:
        assert call.kwargs["request_config"].read_timeout == 2.5


def test_exhausted_retries_name_the_last_failure() -> None:
    http_client = Mock()
    http_client.send.side_effect = [_token(), _response(500), _response(503)]

    with patch("aws_credentials_imds.client.time.sleep"):
        with pytest.raises(
            SmithyIdentityError, match=r"after 2 attempt\(s\): IMDS returned 503"
        ):
            _get(http_client, IMDSConfig(max_attempts=2))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError(), True),
        (ClientTimeoutError(), True),
        (ConnectionResetError(), False),
    ],
)
def test_request_error_flags_timeouts(error: Exception, expected: bool) -> None:
    http_client = Mock()
    http_client.send.side_effect = error

    with pytest.raises(SmithyIdentityError) as exc:
        _get(http_client, IMDSConfig(max_attempts=1))

    request_error = exc.value.__cause__
    assert getattr(request_error, "is_timeout_error") is expected
