# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import GetObjectInput, PutObjectInput
from smithy_test import mock


def test_should_not_add_content_length_if_no_body() -> None:
    """A request without a body omits content-length."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            headers=lambda headers: "content-length" not in headers
        )

        client.get_object(GetObjectInput(bucket="b", key="k"))


# TODO: send a checksum header and content-length for bodies of known length in place of an aws-chunked trailer
@pytest.mark.skip
def test_should_add_content_length_if_body_present() -> None:
    """A request with a body carries its content-length."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(headers={"content-length": "/4/"})

        client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))
