# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import (
    CreateBucketConfiguration,
    CreateBucketInput,
    Delete,
    DeleteObjectsInput,
    GetObjectInput,
    HeadBucketInput,
    LocationInfo,
    PutObjectInput,
)
from smithy_test import mock

BUCKET = "test-bucket--usw2-az1--x-s3"

BUCKET_HOST = f"{BUCKET}.s3express-usw2-az1.us-west-2.amazonaws.com"

CREATE_SESSION_RESULT = """<?xml version="1.0" encoding="UTF-8"?>
<CreateSessionResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Credentials>
    <SessionToken>S3_EXPRESS_SESSION_TOKEN</SessionToken>
    <SecretAccessKey>S3_EXPRESS_SECRET_ACCESS_KEY</SecretAccessKey>
    <AccessKeyId>S3_EXPRESS_ACCESS_KEY_ID</AccessKeyId>
    <Expiration>2100-01-01T00:00:00Z</Expiration>
  </Credentials>
</CreateSessionResult>"""


# TODO: add the sigv4-s3express auth scheme
@pytest.mark.skip
def test_should_not_send_the_x_amz_create_session_mode_header() -> None:
    """A directory bucket request omits the x-amz-create-session-mode header."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname=BUCKET_HOST, query={"session": ""}).respond_with(
        body=CREATE_SESSION_RESULT
    )
    controller.expect_request(hostname=BUCKET_HOST, path="/1")

    client.get_object(GetObjectInput(bucket=BUCKET, key="1"))

    headers = [f.name.lower() for f in controller.requests[-1].fields]
    assert "x-amz-create-session-mode" not in headers


# TODO: add the sigv4-s3express auth scheme
@pytest.mark.skip
def test_should_default_to_crc32_checksum_when_the_request_requires_a_checksum_and_none_is_specified() -> (
    None
):
    """A directory bucket request that requires a checksum defaults to CRC32 in place of Content-MD5."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname=BUCKET_HOST, query={"session": ""}).respond_with(
        body=CREATE_SESSION_RESULT
    )
    controller.expect_request(
        hostname=BUCKET_HOST, headers={"x-amz-checksum-crc32": "b9SZTg=="}
    )

    client.delete_objects(DeleteObjectsInput(bucket=BUCKET, delete=Delete(objects=[])))

    headers = [f.name.lower() for f in controller.requests[-1].fields]
    assert "content-md5" not in headers


def test_does_not_fill_a_default_create_bucket_configuration_location_constraint() -> (
    None
):
    """CreateBucket for a directory bucket keeps the location from the caller and omits LocationConstraint."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(body=lambda body: b"LocationConstraint" not in body)

    client.create_bucket(
        CreateBucketInput(
            bucket=BUCKET,
            create_bucket_configuration=CreateBucketConfiguration(
                location=LocationInfo(type="AvailabilityZone", name="usw2-az1")
            ),
        )
    )

    headers = [f.name.lower() for f in controller.requests[-1].fields]
    assert "content-md5" not in headers


# TODO: add the sigv4-s3express auth scheme
@pytest.mark.skip
def test_should_use_the_session_token_header_instead_of_the_security_token_header() -> (
    None
):
    """Directory bucket requests carry x-amz-s3session-token in place of x-amz-security-token."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname=BUCKET_HOST, query={"session": ""}).respond_with(
        body=CREATE_SESSION_RESULT
    )
    controller.expect_request(
        hostname=BUCKET_HOST,
        headers={"x-amz-s3session-token": "S3_EXPRESS_SESSION_TOKEN"},
    )

    client.put_object(PutObjectInput(bucket=BUCKET, key="test.json", body=b"{}"))

    headers = [f.name.lower() for f in controller.requests[-1].fields]
    assert "x-amz-security-token" not in headers


# TODO: add the sigv4-s3express auth scheme
@pytest.mark.skip
def test_should_feature_detect_s3_express_bucket() -> None:
    """The user agent lists the feature ID for S3 Express."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname=BUCKET_HOST, query={"session": ""}).respond_with(
        body=CREATE_SESSION_RESULT
    )
    # "J" is the S3_EXPRESS_BUCKET business metric.
    controller.expect_request(
        hostname=BUCKET_HOST,
        headers={
            "user-agent": lambda ua: (
                (metrics := re.search(r" m/(\S*)", ua)) is not None
                and "J" in metrics.group(1).split(",")
            )
        },
    )

    client.head_bucket(HeadBucketInput(bucket=BUCKET))
