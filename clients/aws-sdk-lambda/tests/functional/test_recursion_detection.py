# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_lambda.client import LambdaClient
from aws_sdk_lambda.config import LambdaConfig
from aws_sdk_lambda.models import InvokeInput
from pytest import MonkeyPatch
from smithy_test import mock


# TODO: add recursion detection from _X_AMZN_TRACE_ID
@pytest.mark.skip
def test_should_create_recursion_detection_headers(monkeypatch: MonkeyPatch) -> None:
    """Inside a Lambda function, the client copies _X_AMZN_TRACE_ID into the X-Amzn-Trace-Id header."""
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "MyLambdaFunction")
    monkeypatch.setenv("_X_AMZN_TRACE_ID", "trace-1234")
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(headers={"X-Amzn-Trace-Id": "/^trace-1234$/"})

    client.invoke(InvokeInput(function_name="my-function"))
