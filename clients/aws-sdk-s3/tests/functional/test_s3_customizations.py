# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import HeadBucketInput, PutObjectInput
from pytest import LogCaptureFixture, raises
from smithy_core.exceptions import SmithyError
from smithy_test import mock


# TODO: validate bucket names before sending
@pytest.mark.skip
def test_validates_bucket_names() -> None:
    """A bucket name with a slash raises InvalidBucketName before any request goes out."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request()

    with raises(SmithyError, match="InvalidBucketName"):
        client.head_bucket(HeadBucketInput(bucket="/my-bucket/a"))

    assert controller.requests == []


# TODO: warn on bodies of unknown length
@pytest.mark.skip
def test_warns_on_input_streams_of_unknown_length(caplog: LogCaptureFixture) -> None:
    """A body of unknown length logs a warning."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(query={"x-id": "PutObject"})

    # A pipe isn't seekable, so its length can't be known up front.
    read_fd, write_fd = os.pipe()
    os.close(write_fd)

    with caplog.at_level(logging.WARNING), open(read_fd, "rb") as body:
        client.put_object(PutObjectInput(bucket="my-bucket", key="k", body=body))

    assert any("unknown length" in record.getMessage() for record in caplog.records), (
        caplog.text
    )


# TODO: add the bucket_endpoint config option
@pytest.mark.skip
def test_allows_using_a_bucket_input_value_as_the_endpoint() -> None:
    """With bucket_endpoint set, the bucket input serves as the endpoint URL."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", bucket_endpoint=True)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    mock(client).expect_request(
        query={"x-id": "PutObject"},
        scheme="https",
        hostname="mybucket.com",
        port="8888",
        path="/my-bucket-path/my-key",
    )

    client.put_object(
        PutObjectInput(
            bucket="https://mybucket.com:8888/my-bucket-path",
            key="my-key",
            body=b"abcd",
        )
    )


def test_considers_missing_bucket_an_http_label_error() -> None:
    """An empty bucket raises an error before any request goes out."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request()

    with raises(SmithyError, match="(?i)bucket"):
        client.head_bucket(HeadBucketInput())

    assert controller.requests == []
