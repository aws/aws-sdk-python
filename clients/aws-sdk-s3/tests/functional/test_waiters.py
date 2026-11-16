# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import HeadObjectInput
from smithy_test import mock


# TODO: generate waiters
@pytest.mark.skip
def test_should_poll_until_a_return_condition_is_met_http_status() -> None:
    # Imported here so the rest of the suite still collects while waiters don't exist.
    """The object-exists waiter polls HeadObject until the status matches its success condition."""
    from aws_sdk_s3.waiters import (  # pyright: ignore[reportMissingImports]
        wait_until_object_exists,  # pyright: ignore[reportUnknownVariableType]
    )

    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(hostname="/s3\\.us-west-2\\.amazonaws\\.com/").times(
            2
        ).respond_with(status_code=404).respond_with(status_code=200)

        wait_until_object_exists(
            client,
            HeadObjectInput(bucket="@@@@", key="####"),
            max_delay=5,
            max_wait_time=20,
        )
