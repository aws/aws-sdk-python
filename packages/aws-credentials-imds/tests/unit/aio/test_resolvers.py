# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from aws_credentials_imds.aio.client import IMDSConfig
from aws_credentials_imds.aio.resolvers import IMDSCredentialsResolver
from smithy_core.exceptions import SmithyIdentityError

ISO8601 = "%Y-%m-%dT%H:%M:%SZ"

_CREDS = {
    "AccessKeyId": "test-access-key",
    "SecretAccessKey": "test-secret-key",
    "Token": "test-session-token",
    "AccountId": "test-account",
    "Expiration": "2025-03-13T07:28:47Z",
}


async def test_resolver_success() -> None:
    http_client = AsyncMock()
    config = IMDSConfig()
    imds_client = AsyncMock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.side_effect = ["test-profile", json.dumps(_CREDS)]

    credentials = await resolver.get_identity(properties={})
    assert credentials.access_key_id == "test-access-key"
    assert credentials.secret_access_key == "test-secret-key"
    assert credentials.session_token == "test-session-token"
    assert credentials.account_id == "test-account"
    assert credentials.expiration == datetime(2025, 3, 13, 7, 28, 47, tzinfo=UTC)
    imds_client.get.assert_awaited()


async def test_resolver_uses_configured_profile_name() -> None:
    http_client = AsyncMock()
    config = IMDSConfig(ec2_instance_profile_name="configured-profile")
    imds_client = AsyncMock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.return_value = json.dumps(_CREDS)

    await resolver.get_identity(properties={})

    # No profile lookup call when profile name is configured
    imds_client.get.assert_awaited_once_with(
        path="/latest/meta-data/iam/security-credentials/configured-profile"
    )


async def test_resolver_caches_credentials() -> None:
    http_client = AsyncMock()
    config = IMDSConfig()
    imds_client = AsyncMock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    future = (datetime.now(UTC) + timedelta(minutes=10)).strftime(ISO8601)
    imds_client.get.side_effect = [
        "test-profile",
        json.dumps({**_CREDS, "Expiration": future}),
    ]

    first = await resolver.get_identity(properties={})
    second = await resolver.get_identity(properties={})

    assert first is second
    # Initial call for profile name, second call for credentials
    assert imds_client.get.await_count == 2


async def test_resolver_refreshes_expired_credentials() -> None:
    http_client = AsyncMock()
    config = IMDSConfig()
    imds_client = AsyncMock()
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

    first = await resolver.get_identity(properties={})
    second = await resolver.get_identity(properties={})

    assert first is not second
    assert first.access_key_id == "expired-key"
    assert second.access_key_id == "fresh-key"
    # Both the profile lookup and credential fetch run again on refresh
    assert imds_client.get.await_count == 4


async def test_resolver_requires_access_key_and_secret() -> None:
    http_client = AsyncMock()
    config = IMDSConfig()
    imds_client = AsyncMock()
    resolver = IMDSCredentialsResolver(http_client, config)
    resolver._imds_client = imds_client

    imds_client.get.side_effect = [
        "test-profile",
        json.dumps({"AccessKeyId": "test-access-key"}),
    ]

    with pytest.raises(
        SmithyIdentityError, match="AccessKeyId and SecretAccessKey are required"
    ):
        await resolver.get_identity(properties={})
