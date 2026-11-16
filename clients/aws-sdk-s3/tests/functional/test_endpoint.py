# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import HeadBucketInput
from smithy_test import mock


def test_should_resolve_endpoints() -> None:
    """A multi-region access point ARN resolves to its FIPS dual-stack access point hostname."""
    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            use_fips_endpoint=True,
            use_dualstack_endpoint=True,
            use_arn_region=True,
        )
    )
    with mock(client) as controller:
        controller.expect_request(
            hostname=r"/mrap-name-1234567890.s3-accesspoint-fips.dualstack.us-east-1.amazonaws.com$/"
        )

        client.head_bucket(
            HeadBucketInput(
                bucket="arn:aws:s3:us-east-1:1234567890:accesspoint:mrap-name"
            )
        )
