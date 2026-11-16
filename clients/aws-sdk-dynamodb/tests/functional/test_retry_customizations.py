# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

import pytest
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import ListTablesInput
from smithy_core.client import RequestPipeline
from smithy_core.exceptions import CallError
from smithy_core.retries import (
    AdaptiveRetryStrategy,
    ExponentialRetryBackoffStrategy,
    StandardRetryStrategy,
)
from smithy_test import mock

# CAUTION: a 408 because the SDK doesn't retry a 5xx, and a 429 makes the adaptive
# rate limiter wait for real.
TIMEOUT_ERROR = (
    '{"__type": "com.amazonaws.dynamodb#RequestTimeout", "message": "Oh No"}'
)
JSON_HEADERS = {"content-type": "application/x-amz-json-1.0"}


def test_defaults_to_4_attempts_with_25ms_delay_base_standard_retry_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Backoff delays are asserted through the strategy, so the waits are skipped.
    """DynamoDB defaults to 4 attempts with a 25 ms backoff base under the standard retry strategy."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )

    with pytest.raises(CallError):
        client.list_tables(ListTablesInput())

    retry_strategy = client._config.retry_strategy
    assert type(retry_strategy) is StandardRetryStrategy
    assert retry_strategy.max_attempts == 4
    assert isinstance(retry_strategy.backoff_strategy, ExponentialRetryBackoffStrategy)
    assert retry_strategy.backoff_strategy._backoff_scale_value == 0.025
    assert len(controller.requests) == 4


def test_preserves_4_attempts_and_25ms_delay_base_if_adaptive_mode_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Backoff delays are asserted through the strategy, so the waits are skipped.
    """Adaptive retry mode keeps the DynamoDB defaults of 4 attempts and a 25 ms backoff base."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(region="us-west-2", retry_mode="adaptive")
    )
    controller = mock(client)
    controller.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )

    with pytest.raises(CallError):
        client.list_tables(ListTablesInput())

    retry_strategy = client._config.retry_strategy
    assert isinstance(retry_strategy, AdaptiveRetryStrategy)
    assert retry_strategy.max_attempts == 4
    assert isinstance(retry_strategy.backoff_strategy, ExponentialRetryBackoffStrategy)
    assert retry_strategy.backoff_strategy._backoff_scale_value == 0.025
    assert len(controller.requests) == 4


def test_preserves_standard_mode_and_25ms_delay_base_if_10_attempts_are_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Backoff delays are asserted through the strategy, so the waits are skipped.
    """Setting 10 max attempts keeps standard mode and the 25 ms backoff base."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2", max_attempts=10))
    controller = mock(client)
    controller.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )

    with pytest.raises(CallError):
        client.list_tables(ListTablesInput())

    retry_strategy = client._config.retry_strategy
    assert type(retry_strategy) is StandardRetryStrategy
    assert retry_strategy.max_attempts == 10
    assert isinstance(retry_strategy.backoff_strategy, ExponentialRetryBackoffStrategy)
    assert retry_strategy.backoff_strategy._backoff_scale_value == 0.025
    assert len(controller.requests) == 10


def test_providing_a_retry_strategy_object_overrides_the_attempt_count_and_delay_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Backoff delays are asserted through the strategy, so the waits are skipped.
    """A retry strategy object from the caller replaces the DynamoDB attempt count and backoff base."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)
    custom = StandardRetryStrategy(
        max_attempts=7,
        backoff_strategy=ExponentialRetryBackoffStrategy(backoff_scale_value=0.1),
    )
    client = DynamoDBClient(
        DynamoDBConfig.resolve(region="us-west-2", retry_strategy=custom)
    )
    controller = mock(client)
    controller.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )

    with pytest.raises(CallError):
        client.list_tables(ListTablesInput())

    retry_strategy = client._config.retry_strategy
    assert retry_strategy is custom
    assert retry_strategy.max_attempts == 7
    assert isinstance(retry_strategy.backoff_strategy, ExponentialRetryBackoffStrategy)
    assert retry_strategy.backoff_strategy._backoff_scale_value == 0.1
    assert len(controller.requests) == 7


def test_resolves_precedence_code_env_ddb_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Backoff delays are asserted through the strategy, so the waits are skipped.
    """Max attempts from code take precedence over the environment, which takes precedence over the DynamoDB default."""
    monkeypatch.setattr(RequestPipeline, "_sleep", _no_sleep)

    monkeypatch.setenv("AWS_MAX_ATTEMPTS", "9")
    client_with_env = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller_with_env = mock(client_with_env)
    controller_with_env.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )
    with pytest.raises(CallError):
        client_with_env.list_tables(ListTablesInput())
    assert client_with_env._config.retry_strategy.max_attempts == 9
    assert len(controller_with_env.requests) == 9

    client_with_code = DynamoDBClient(
        DynamoDBConfig.resolve(region="us-west-2", max_attempts=5)
    )
    controller_with_code = mock(client_with_code)
    controller_with_code.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )
    with pytest.raises(CallError):
        client_with_code.list_tables(ListTablesInput())
    assert client_with_code._config.retry_strategy.max_attempts == 5
    assert len(controller_with_code.requests) == 5

    monkeypatch.delenv("AWS_MAX_ATTEMPTS")
    client_default = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller_default = mock(client_default)
    controller_default.expect_request().respond_with(
        status_code=408, headers=JSON_HEADERS, body=TIMEOUT_ERROR
    )
    with pytest.raises(CallError):
        client_default.list_tables(ListTablesInput())
    assert client_default._config.retry_strategy.max_attempts == 4
    assert len(controller_default.requests) == 4


def _no_sleep(self: RequestPipeline[Any, Any], delay: float) -> None:
    pass
