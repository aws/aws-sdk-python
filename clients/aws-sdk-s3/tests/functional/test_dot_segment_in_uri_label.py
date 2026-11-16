# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import GetObjectInput
from smithy_test import mock


def test_s3_preserves_leading_dot_segment_in_uri_label() -> None:
    """A key that starts with a dot segment keeps it in the request path."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            method="GET",
            hostname="mybucket.s3.us-west-2.amazonaws.com",
            path="/../key.txt",
        )

        client.get_object(GetObjectInput(bucket="mybucket", key="../key.txt"))


def test_s3_preserves_embedded_dot_segment_in_uri_label() -> None:
    """A key that contains a dot segment keeps it in the request path."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            method="GET",
            hostname="mybucket.s3.us-west-2.amazonaws.com",
            path="/foo/../key.txt",
        )

        client.get_object(GetObjectInput(bucket="mybucket", key="foo/../key.txt"))
