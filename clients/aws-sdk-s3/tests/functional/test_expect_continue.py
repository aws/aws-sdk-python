# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import ListBucketsInput, PutObjectInput
from smithy_test import mock


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_not_set_expect_header_if_there_is_no_body() -> None:
    """A request without a body omits the Expect header."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=True)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    controller = mock(client)
    controller.expect_request()

    client.list_buckets(ListBucketsInput())

    assert "expect" not in [f.name.lower() for f in controller.requests[0].fields]


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_set_expect_header_if_there_is_a_body() -> None:
    """A request with a body carries `Expect: 100-continue`."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=4)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    mock(client).expect_request(headers={"Expect": "100-continue"})

    client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_omit_expect_header_when_disabled() -> None:
    """Setting expect_continue_header to False omits the Expect header."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=False)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    controller = mock(client)
    controller.expect_request()

    client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))

    assert "expect" not in [f.name.lower() for f in controller.requests[0].fields]


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_omit_expect_header_when_body_is_below_threshold() -> None:
    """A 5-byte threshold omits the Expect header for a 4-byte body."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=5)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    controller = mock(client)
    controller.expect_request()

    client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))

    assert "expect" not in [f.name.lower() for f in controller.requests[0].fields]


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_set_expect_header_when_enabled() -> None:
    """Setting expect_continue_header to True adds the Expect header."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=True)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    mock(client).expect_request(headers={"Expect": "100-continue"})

    client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))


# TODO: add the expect_continue_header config option
@pytest.mark.skip
def test_should_set_expect_header_when_body_meets_threshold() -> None:
    """A 4-byte threshold adds the Expect header for a 4-byte body."""
    client = S3Client(
        S3Config.resolve(region="us-west-2", expect_continue_header=4)  # pyright: ignore[reportCallIssue, reportUnknownArgumentType]
    )
    mock(client).expect_request(headers={"Expect": "100-continue"})

    client.put_object(PutObjectInput(bucket="b", key="k", body=b"abcd"))
