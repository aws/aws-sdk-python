# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_lambda.client import LambdaClient
from aws_sdk_lambda.config import LambdaConfig
from aws_sdk_lambda.models import InvokeInput
from smithy_test import mock


# TODO: send the amz-sdk-invocation-id and amz-sdk-request headers
@pytest.mark.skip
def test_should_set_retry_headers() -> None:
    """Requests carry the amz-sdk-invocation-id and amz-sdk-request retry headers."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        hostname="lambda.us-west-2.amazonaws.com",
        headers={
            "amz-sdk-invocation-id": r"/^[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}$/",
            "amz-sdk-request": "attempt=1; max=3",
        },
    )

    client.invoke(InvokeInput(function_name="my-function"))
