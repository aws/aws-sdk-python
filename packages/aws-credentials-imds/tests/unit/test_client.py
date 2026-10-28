# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import time

from aws_credentials_imds.client import IMDSToken


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
