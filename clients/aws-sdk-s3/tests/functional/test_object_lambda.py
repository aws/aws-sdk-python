# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import GetObjectInput
from smithy_test import mock


def test_can_make_a_get_request_to_an_s3_object_lambda_arn() -> None:
    """GetObject on an Object Lambda access point ARN, in slash or colon form, goes to the Object Lambda hostname with an s3-object-lambda signature."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            hostname="my-access-point-123456789012.s3-object-lambda.us-west-2.amazonaws.com",
            query={"x-id": "GetObject"},
            # CAUTION: the mock signs with its own access key, so it precedes the date.
            headers={
                "authorization": r"/=\w+/\d+/us-west-2/s3-object-lambda/aws4_request/"
            },
            path="/a",
        ).times(2)

        # slash delimiter
        client.get_object(
            GetObjectInput(
                bucket="arn:aws:s3-object-lambda:us-west-2:123456789012:accesspoint/my-access-point",
                key="a",
            )
        )
        # colon delimiter
        client.get_object(
            GetObjectInput(
                bucket="arn:aws:s3-object-lambda:us-west-2:123456789012:accesspoint:my-access-point",
                key="a",
            )
        )
