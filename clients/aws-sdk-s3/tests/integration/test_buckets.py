# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Bucket lifecycle and configuration, from JS v3 s3-bucket-features.e2e."""

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.models import (
    BucketLifecycleConfiguration,
    CORSConfiguration,
    CORSRule,
    CreateBucketInput,
    DeleteBucketInput,
    ExpirationStatus,
    GetBucketCorsInput,
    GetBucketLifecycleConfigurationInput,
    GetBucketLocationInput,
    GetBucketTaggingInput,
    HeadBucketInput,
    LifecycleExpiration,
    LifecycleRule,
    LifecycleRuleFilter,
    ListBucketsInput,
    NoSuchBucket,
    NotFound,
    PutBucketCorsInput,
    PutBucketLifecycleConfigurationInput,
    PutBucketTaggingInput,
    Tag,
    Tagging,
)
from waiters import wait_until, wait_until_gone

from . import (
    OTHER_REGION,
    REGION,
    ClientOptions,
    NotVisibleYet,
    in_region,
    unique_bucket_name,
    until_visible,
)
from .conftest import S3Factory


async def test_create_head_list_delete_bucket(s3: AsyncS3Client) -> None:
    name = unique_bucket_name()
    await s3.create_bucket(
        CreateBucketInput(bucket=name, create_bucket_configuration=in_region(REGION))
    )
    try:
        await wait_until(
            lambda: s3.head_bucket(HeadBucketInput(bucket=name)),
            retry_on=(NotFound, NoSuchBucket),
            interval=2,
        )
        listed = await wait_until(
            lambda: s3.list_buckets(ListBucketsInput(prefix=name)),
            lambda out: [b.name for b in out.buckets or []] == [name],
            interval=2,
        )
        assert [b.name for b in listed.buckets or []] == [name]
        location = await wait_until(
            lambda: s3.get_bucket_location(GetBucketLocationInput(bucket=name)),
            retry_on=(NoSuchBucket,),
            interval=2,
        )
        assert location.location_constraint == REGION
    finally:
        await s3.delete_bucket(DeleteBucketInput(bucket=name))
        await wait_until_gone(
            lambda: s3.head_bucket(HeadBucketInput(bucket=name)),
            gone_on=(NotFound, NoSuchBucket),
            interval=2,
        )


async def test_create_bucket_in_other_region(make_s3: S3Factory) -> None:
    s3 = await make_s3(ClientOptions(region=OTHER_REGION))
    name = unique_bucket_name()
    await s3.create_bucket(
        CreateBucketInput(
            bucket=name, create_bucket_configuration=in_region(OTHER_REGION)
        )
    )
    try:
        location = await wait_until(
            lambda: s3.get_bucket_location(GetBucketLocationInput(bucket=name)),
            retry_on=(NoSuchBucket,),
            interval=2,
        )
        assert location.location_constraint == OTHER_REGION
    finally:
        await s3.delete_bucket(DeleteBucketInput(bucket=name))
        await wait_until_gone(
            lambda: s3.head_bucket(HeadBucketInput(bucket=name)),
            gone_on=(NotFound, NoSuchBucket),
            interval=2,
        )


@pytest.mark.skip(reason="CreateBucket does not fill LocationConstraint from region.")
async def test_create_bucket_defaults_location_constraint_to_region() -> None: ...


async def test_bucket_cors(s3: AsyncS3Client, bucket: str) -> None:
    rule = CORSRule(
        allowed_methods=["GET", "PUT"],
        allowed_origins=["https://example.com"],
        allowed_headers=["*"],
        max_age_seconds=3000,
    )
    await s3.put_bucket_cors(
        PutBucketCorsInput(
            bucket=bucket, cors_configuration=CORSConfiguration(cors_rules=[rule])
        )
    )
    cors = await wait_until(
        until_visible(lambda: s3.get_bucket_cors(GetBucketCorsInput(bucket=bucket))),
        lambda out: bool(out.cors_rules),
        retry_on=(NotVisibleYet,),
        interval=2,
    )
    assert cors.cors_rules is not None
    assert cors.cors_rules[0].allowed_methods == ["GET", "PUT"]
    assert cors.cors_rules[0].allowed_origins == ["https://example.com"]
    assert cors.cors_rules[0].max_age_seconds == 3000


async def test_bucket_lifecycle(s3: AsyncS3Client, bucket: str) -> None:
    rule = LifecycleRule(
        id="expire-tmp",
        status=ExpirationStatus.ENABLED,
        filter=LifecycleRuleFilter(prefix="tmp/"),
        expiration=LifecycleExpiration(days=1),
    )
    await s3.put_bucket_lifecycle_configuration(
        PutBucketLifecycleConfigurationInput(
            bucket=bucket,
            lifecycle_configuration=BucketLifecycleConfiguration(rules=[rule]),
        )
    )
    lifecycle = await wait_until(
        until_visible(
            lambda: s3.get_bucket_lifecycle_configuration(
                GetBucketLifecycleConfigurationInput(bucket=bucket)
            )
        ),
        lambda out: bool(out.rules),
        retry_on=(NotVisibleYet,),
        interval=2,
    )
    assert lifecycle.rules is not None
    assert lifecycle.rules[0].id == "expire-tmp"
    assert lifecycle.rules[0].expiration is not None
    assert lifecycle.rules[0].expiration.days == 1


async def test_bucket_tagging(s3: AsyncS3Client, bucket: str) -> None:
    tags = [Tag(key="purpose", value="integ"), Tag(key="sdk", value="python")]
    await s3.put_bucket_tagging(
        PutBucketTaggingInput(bucket=bucket, tagging=Tagging(tag_set=tags))
    )
    tagging = await wait_until(
        until_visible(
            lambda: s3.get_bucket_tagging(GetBucketTaggingInput(bucket=bucket))
        ),
        lambda out: len(out.tag_set or []) == len(tags),
        retry_on=(NotVisibleYet,),
        interval=2,
    )
    assert {(t.key, t.value) for t in tagging.tag_set or []} == {
        ("purpose", "integ"),
        ("sdk", "python"),
    }


@pytest.mark.skip(reason="Following S3 region redirects is not implemented.")
async def test_requests_follow_region_redirect() -> None: ...


@pytest.mark.skip(reason="Client-side bucket name validation is not implemented.")
async def test_invalid_bucket_name_rejected_before_sending() -> None: ...


@pytest.mark.skip(reason="S3 Express directory bucket session auth is not implemented.")
async def test_directory_bucket_crud() -> None: ...
