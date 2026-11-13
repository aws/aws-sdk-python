# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Multipart uploads, from JS v3 S3.e2e MultipartUpload."""

import os

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.models import (
    AbortMultipartUploadInput,
    CompletedMultipartUpload,
    CompletedPart,
    CompleteMultipartUploadInput,
    CreateMultipartUploadInput,
    GetObjectInput,
    ListMultipartUploadsInput,
    ListPartsInput,
    UploadPartInput,
)

from . import read_body

# Every part except the last must be at least 5 MiB.
_PART_SIZE = 5 * 1024 * 1024


async def test_create_upload_list_complete(s3: AsyncS3Client, bucket: str) -> None:
    key = f"multipart/{os.urandom(4).hex()}"
    parts = [os.urandom(_PART_SIZE), os.urandom(1024)]
    upload = await s3.create_multipart_upload(
        CreateMultipartUploadInput(bucket=bucket, key=key)
    )
    assert upload.upload_id is not None

    completed: list[CompletedPart] = []
    for number, data in enumerate(parts, start=1):
        part = await s3.upload_part(
            UploadPartInput(
                bucket=bucket,
                key=key,
                upload_id=upload.upload_id,
                part_number=number,
                body=data,
            )
        )
        completed.append(
            CompletedPart(
                part_number=number, e_tag=part.e_tag, checksum_crc32=part.checksum_crc32
            )
        )

    listed = await s3.list_parts(
        ListPartsInput(bucket=bucket, key=key, upload_id=upload.upload_id)
    )
    assert [p.part_number for p in listed.parts or []] == [1, 2]

    await s3.complete_multipart_upload(
        CompleteMultipartUploadInput(
            bucket=bucket,
            key=key,
            upload_id=upload.upload_id,
            multipart_upload=CompletedMultipartUpload(parts=completed),
        )
    )
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == b"".join(parts)


async def test_create_abort_list(s3: AsyncS3Client, bucket: str) -> None:
    key = f"multipart/{os.urandom(4).hex()}"
    upload = await s3.create_multipart_upload(
        CreateMultipartUploadInput(bucket=bucket, key=key)
    )
    await s3.abort_multipart_upload(
        AbortMultipartUploadInput(bucket=bucket, key=key, upload_id=upload.upload_id)
    )
    uploads = await s3.list_multipart_uploads(
        ListMultipartUploadsInput(bucket=bucket, prefix=key)
    )
    assert not uploads.uploads


@pytest.mark.skip(reason="A managed multipart upload helper is not implemented.")
async def test_managed_upload() -> None: ...


@pytest.mark.skip(
    reason="Retrying 200 responses with an error body is not implemented."
)
async def test_complete_multipart_upload_retries_200_error() -> None: ...
