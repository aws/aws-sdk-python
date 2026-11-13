# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import (
    CreateBucketConfiguration,
    CreateBucketInput,
    LocationInfo,
    Tag,
)
from smithy_test import mock


# TODO: fill CreateBucket LocationConstraint from the client region
@pytest.mark.skip
def test_should_default_location_constraint_from_region() -> None:
    """CreateBucket fills LocationConstraint from the client region."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(
        body="/<CreateBucketConfiguration (.*)?><LocationConstraint>us-west-2"
        "</LocationConstraint></CreateBucketConfiguration>/"
    )

    client.create_bucket(CreateBucketInput(bucket="b"))


def test_should_not_default_location_constraint_in_us_east_1() -> None:
    """CreateBucket in us-east-1 sends no LocationConstraint."""
    client = S3Client(S3Config.resolve(region="us-east-1"))
    mock(client).expect_request(body=lambda body: b"LocationConstraint" not in body)

    client.create_bucket(CreateBucketInput(bucket="b"))


def test_should_populate_other_elements_of_the_create_bucket_configuration_regardless_of_location_or_location_constraint() -> (
    None
):
    """CreateBucket keeps the other CreateBucketConfiguration elements from the caller."""
    client = S3Client(S3Config.resolve(region="us-east-1"))
    mock(client).expect_request(
        body=lambda body: (
            b'<CreateBucketConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            b"<Tags><Tag><Key>my-tag-key</Key><Value>my-tag-value</Value></Tag></Tags>"
            b"</CreateBucketConfiguration>" in body
        )
    )

    client.create_bucket(
        CreateBucketInput(
            bucket="b",
            create_bucket_configuration=CreateBucketConfiguration(
                tags=[Tag(key="my-tag-key", value="my-tag-value")]
            ),
        )
    )


def test_should_not_default_location_constraint_for_directory_buckets() -> None:
    """CreateBucket for a directory bucket sends no default LocationConstraint."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(
        hostname="/-control.us-west-2.amazonaws.com$/",
        body=lambda body: b"LocationConstraint" not in body,
    )

    client.create_bucket(
        CreateBucketInput(
            bucket="s3-express-1234--usw2-az2--x-s3",
            create_bucket_configuration=CreateBucketConfiguration(
                location=LocationInfo(type="AvailabilityZone", name="usw2-az2")
            ),
        )
    )
