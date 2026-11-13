# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import time

import pytest
from aws_sdk_sqs.client import SQSClient
from aws_sdk_sqs.config import SQSConfig
from aws_sdk_sqs.models import ReceiveMessageInput
from pytest import raises
from smithy_core.exceptions import CallError
from smithy_core.retries import (
    ExponentialBackoffJitterType,
    ExponentialRetryBackoffStrategy,
    StandardRetryQuota,
    StandardRetryStrategy,
)
from smithy_test import mock


# TODO: retry 500 responses without a modeled error
@pytest.mark.skip
def test_performs_retry_in_a_long_poll_mode() -> None:
    """ReceiveMessage retries a 500 response with a backoff in long poll mode."""
    client = SQSClient(
        SQSConfig.resolve(
            region="us-west-2",
            retry_strategy=StandardRetryStrategy(
                # Deterministic backoff: 50ms, 100ms, 200ms.
                backoff_strategy=ExponentialRetryBackoffStrategy(
                    backoff_scale_value=0.05,
                    jitter_type=ExponentialBackoffJitterType.NONE,
                ),
                max_attempts=4,
                # Two transient retries cost 14 each, so the third is denied.
                retry_quota=StandardRetryQuota(initial_capacity=28),
            ),
        )
    )
    controller = mock(client)
    controller.expect_request(hostname="sqs.us-west-2.amazonaws.com").respond_with(
        status_code=500
    )

    request_begins = time.monotonic()
    with raises(CallError):
        client.receive_message(
            ReceiveMessageInput(
                queue_url="https://sqs.us-west-2.amazonaws.com/000000000000/Glorp"
            )
        )
    time_elapsed = time.monotonic() - request_begins

    assert len(controller.requests) == 3
    # 150ms from the two retries plus 200ms of long-poll backoff once the quota
    # is exhausted.
    assert time_elapsed >= 0.35
