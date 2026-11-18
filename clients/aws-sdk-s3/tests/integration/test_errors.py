# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Error handling, from JS v3 S3.e2e error handling and ListObjects."""

import os

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.models import (
    AbortMultipartUploadInput,
    GetObjectInput,
    HeadObjectInput,
    ListObjectsV2Input,
    NoSuchBucket,
    NoSuchKey,
    NoSuchUpload,
    NotFound,
)

from . import unique_bucket_name


async def test_no_such_key_carries_response_metadata(
    s3: AsyncS3Client, bucket: str
) -> None:
    with pytest.raises(NoSuchKey) as caught:
        await s3.get_object(
            GetObjectInput(bucket=bucket, key=f"missing/{os.urandom(4).hex()}")
        )

    error = caught.value
    assert error.message
    assert error.fault == "client"
    metadata = error.response_metadata
    assert metadata.http_status_code == 404
    assert metadata.request_id
    assert metadata.extended_request_id


async def test_head_missing_object_is_not_found(s3: AsyncS3Client, bucket: str) -> None:
    # HEAD responses have no body, so the error comes from the status code alone.
    with pytest.raises(NotFound) as caught:
        await s3.head_object(
            HeadObjectInput(bucket=bucket, key=f"missing/{os.urandom(4).hex()}")
        )
    assert caught.value.response_metadata.http_status_code == 404


async def test_no_such_bucket(s3: AsyncS3Client) -> None:
    with pytest.raises(NoSuchBucket):
        await s3.list_objects_v2(
            ListObjectsV2Input(bucket=unique_bucket_name("missing-"))
        )


async def test_no_such_upload(s3: AsyncS3Client, bucket: str) -> None:
    with pytest.raises(NoSuchUpload):
        await s3.abort_multipart_upload(
            AbortMultipartUploadInput(
                bucket=bucket, key="missing", upload_id="not-an-upload"
            )
        )
