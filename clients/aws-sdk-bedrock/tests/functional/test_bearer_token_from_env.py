# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_bedrock.client import BedrockClient
from aws_sdk_bedrock.config import BedrockConfig
from pytest import MonkeyPatch
from smithy_test import mock

MOCK_BEARER_TOKEN = "mock-bearer-token"


# TODO: resolve a bearer token from AWS_BEARER_TOKEN_BEDROCK
@pytest.mark.skip
def test_when_environment_bearer_token_is_set(monkeypatch: MonkeyPatch) -> None:
    """With AWS_BEARER_TOKEN_BEDROCK set, the client authenticates with that token as a bearer token."""
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", MOCK_BEARER_TOKEN)
    client = BedrockClient(
        BedrockConfig.resolve(
            region="us-west-2", aws_access_key_id="INTEG", aws_secret_access_key="INTEG"
        )
    )
    mock(client).expect_request(
        headers={"authorization": f"Bearer {MOCK_BEARER_TOKEN}"}
    )

    client.list_custom_models()


# TODO: add the auth_scheme_preference config option
@pytest.mark.skip
def test_can_be_overridden_by_auth_scheme_preference(monkeypatch: MonkeyPatch) -> None:
    """An auth scheme preference for SigV4 takes precedence over a bearer token from the environment."""
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", MOCK_BEARER_TOKEN)
    client = BedrockClient(
        BedrockConfig.resolve(  # pyright: ignore[reportUnknownArgumentType]
            region="us-west-2",
            aws_access_key_id="INTEG",
            aws_secret_access_key="INTEG",
            auth_scheme_preference=["sigv4"],  # pyright: ignore[reportCallIssue]
        )
    )
    mock(client).expect_request(
        hostname="/bedrock/", headers={"authorization": "/AWS4-HMAC-SHA256 Credential/"}
    )

    client.list_custom_models()


def test_when_environment_bearer_token_is_not_set(monkeypatch: MonkeyPatch) -> None:
    """Without AWS_BEARER_TOKEN_BEDROCK, the client signs the request with SigV4."""
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    client = BedrockClient(
        BedrockConfig.resolve(
            region="us-west-2", aws_access_key_id="INTEG", aws_secret_access_key="INTEG"
        )
    )
    mock(client).expect_request(
        hostname="/bedrock/", headers={"authorization": "/AWS4-HMAC-SHA256 Credential/"}
    )

    client.list_custom_models()
