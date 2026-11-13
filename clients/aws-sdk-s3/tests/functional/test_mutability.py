# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import HeadBucketInput
from smithy_core.interceptors import InputContext, Interceptor
from smithy_test import mock


def test_should_allow_reusing_and_modifying_an_input_object() -> None:
    """One input object reused across calls reflects its latest bucket in each request, and an interceptor edit persists on it."""

    class InputModifyingInterceptor(Interceptor[Any, Any, Any, Any]):
        def modify_before_serialization(self, context: InputContext[Any]) -> Any:
            context.request.expected_bucket_owner = "me"
            return context.request

    def input_modifying_plugin(config: S3Config) -> None:
        config.interceptors.append(InputModifyingInterceptor())

    client = S3Client(
        S3Config.resolve(region="us-west-2"), plugins=[input_modifying_plugin]
    )
    with mock(client) as controller:
        controller.expect_request(
            headers={"x-amz-expected-bucket-owner": "/^me$/"}
        ).times(4)

        params = HeadBucketInput(bucket="bucket1")
        client.head_bucket(params)
        params.bucket = "bucket2"
        client.head_bucket(params)
        params.bucket = "bucket3"
        client.head_bucket(params)
        params.bucket = "bucket4"
        client.head_bucket(params)

    assert [request.destination.host for request in controller.requests] == [
        "bucket1.s3.us-west-2.amazonaws.com",
        "bucket2.s3.us-west-2.amazonaws.com",
        "bucket3.s3.us-west-2.amazonaws.com",
        "bucket4.s3.us-west-2.amazonaws.com",
    ]
    assert params == HeadBucketInput(bucket="bucket4", expected_bucket_owner="me")
