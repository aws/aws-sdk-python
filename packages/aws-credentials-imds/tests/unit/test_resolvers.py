# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import pytest
from aws_credentials_imds.client import IMDSConfig
from aws_credentials_imds.resolvers import IMDSCredentialsResolver
from smithy_core.exceptions import SmithyIdentityError
from smithy_http import Fields

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"

_CREDS = {
    "AccessKeyId": "test-access-key",
    "SecretAccessKey": "test-secret-key",
    "Token": "test-session-token",
    "AccountId": "test-account",
    "Expiration": "2025-03-13T07:28:47Z",
}


def test_resolver_success() -> None:
    http_client = Mock()
    config = IMDSConfig()
    imds_client = Mock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.side_effect = ["test-profile", json.dumps(_CREDS)]

    credentials = resolver.get_identity(properties={})
    assert credentials.access_key_id == "test-access-key"
    assert credentials.secret_access_key == "test-secret-key"
    assert credentials.session_token == "test-session-token"
    assert credentials.account_id == "test-account"
    assert credentials.expiration == datetime(2025, 3, 13, 7, 28, 47, tzinfo=UTC)
    imds_client.get.assert_called()


def test_resolver_uses_configured_profile_name() -> None:
    http_client = Mock()
    config = IMDSConfig(ec2_instance_profile_name="configured-profile")
    imds_client = Mock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.return_value = json.dumps(_CREDS)

    resolver.get_identity(properties={})

    # No profile lookup call when profile name is configured
    imds_client.get.assert_called_once_with(
        path="/latest/meta-data/iam/security-credentials/configured-profile"
    )


def test_resolver_caches_credentials() -> None:
    http_client = Mock()
    config = IMDSConfig()
    imds_client = Mock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    future = (datetime.now(UTC) + timedelta(minutes=10)).strftime(ISO8601)
    imds_client.get.side_effect = [
        "test-profile",
        json.dumps({**_CREDS, "Expiration": future}),
    ]

    first = resolver.get_identity(properties={})
    second = resolver.get_identity(properties={})

    assert first is second
    # Initial call for profile name, second call for credentials
    assert imds_client.get.call_count == 2


def test_resolver_refreshes_expired_credentials() -> None:
    http_client = Mock()
    config = IMDSConfig()
    imds_client = Mock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    past = (datetime.now(UTC) - timedelta(minutes=10)).strftime(ISO8601)
    future = (datetime.now(UTC) + timedelta(minutes=10)).strftime(ISO8601)
    imds_client.get.side_effect = [
        "test-profile",
        json.dumps({**_CREDS, "AccessKeyId": "expired-key", "Expiration": past}),
        "test-profile",
        json.dumps({**_CREDS, "AccessKeyId": "fresh-key", "Expiration": future}),
    ]

    first = resolver.get_identity(properties={})
    second = resolver.get_identity(properties={})

    assert first is not second
    assert first.access_key_id == "expired-key"
    assert second.access_key_id == "fresh-key"
    # Both the profile lookup and credential fetch run again on refresh
    assert imds_client.get.call_count == 4


def test_resolver_requires_access_key_and_secret() -> None:
    http_client = Mock()
    config = IMDSConfig()
    imds_client = Mock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.side_effect = [
        "test-profile",
        json.dumps({"AccessKeyId": "test-access-key"}),
    ]

    with pytest.raises(
        SmithyIdentityError, match="AccessKeyId and SecretAccessKey are required"
    ):
        resolver.get_identity(properties={})


def _ok_responses(*bodies: bytes) -> list[Mock]:
    return [Mock(status=200, body=body, fields=Fields()) for body in bodies]


def test_resolver_owns_one_default_http_client() -> None:
    expired = {**_CREDS, "Expiration": "2000-01-01T00:00:00Z"}
    http_client = Mock()
    http_client.send.side_effect = _ok_responses(
        b"token",
        b"test-profile",
        json.dumps(expired).encode(),
        # No second token request: the token is reused across calls.
        b"test-profile",
        json.dumps(_CREDS).encode(),
    )
    with patch(
        "aws_credentials_imds.resolvers.Urllib3HTTPClient", return_value=http_client
    ) as default_client:
        resolver = IMDSCredentialsResolver()
        resolver.get_identity(properties={})
        resolver.get_identity(properties={})

    default_client.assert_called_once()
    assert http_client.send.call_count == 5
    token_requests = [
        call
        for call in http_client.send.call_args_list
        if call.kwargs["request"].method == "PUT"
    ]
    assert len(token_requests) == 1


@pytest.mark.parametrize(
    ("config", "expected"), [(None, 1.0), (IMDSConfig(timeout=2.5), 2.5)]
)
def test_resolver_default_http_client_uses_config_timeout(
    config: IMDSConfig | None, expected: float
) -> None:
    with patch("aws_credentials_imds.resolvers.Urllib3HTTPClient") as default_client:
        IMDSCredentialsResolver(config=config)

    client_config = default_client.call_args.kwargs["client_config"]
    assert client_config.connect_timeout == expected
    assert client_config.read_timeout == expected


def test_resolver_shares_token_between_concurrent_threads() -> None:
    callers = 10
    # Hold the token request so every caller reaches the token cache before the
    # first token arrives.
    release = threading.Event()
    lock = threading.Lock()
    methods: list[str] = []

    def send(*, request: Any, request_config: Any) -> Mock:
        with lock:
            methods.append(request.method)
        if request.method == "PUT":
            release.wait(timeout=5)
            return Mock(status=200, body=b"token", fields=Fields())
        if request.destination.path.endswith("/test-profile"):
            return Mock(status=200, body=json.dumps(_CREDS).encode(), fields=Fields())
        return Mock(status=200, body=b"test-profile", fields=Fields())

    http_client = Mock()
    http_client.send.side_effect = send
    with patch(
        "aws_credentials_imds.resolvers.Urllib3HTTPClient", return_value=http_client
    ):
        resolver = IMDSCredentialsResolver()
        with ThreadPoolExecutor(callers) as pool:
            futures = [
                pool.submit(resolver.get_identity, properties={})
                for _ in range(callers)
            ]
            time.sleep(0.2)
            release.set()
            results = [future.result(timeout=5) for future in futures]

    assert all(r.access_key_id == "test-access-key" for r in results)
    assert methods.count("PUT") == 1
