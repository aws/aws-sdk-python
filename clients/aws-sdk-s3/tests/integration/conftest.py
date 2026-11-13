# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the S3 integration tests.

The session ``bucket`` is created and torn down with the sync client, so it
never depends on an event loop. ``s3`` and ``make_s3`` are parametrized over
both client modes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.models import (
    AbortMultipartUploadInput,
    BlockedEncryptionTypes,
    CreateBucketInput,
    Delete,
    DeleteBucketInput,
    DeleteObjectsInput,
    EncryptionType,
    ListMultipartUploadsInput,
    ListObjectsV2Input,
    ObjectIdentifier,
    PutBucketEncryptionInput,
    ServerSideEncryption,
    ServerSideEncryptionByDefault,
    ServerSideEncryptionConfiguration,
    ServerSideEncryptionRule,
)
from dual_mode import MODES, Mode, open_client

from . import (
    REGION,
    ClientOptions,
    create_async_client,
    create_sync_client,
    in_region,
    unique_bucket_name,
)

type S3Factory = Callable[[ClientOptions], Awaitable[AsyncS3Client]]


def empty_and_delete_bucket(client: S3Client, bucket: str) -> None:
    """Remove every object and in-progress upload, then the bucket itself."""
    uploads = client.list_multipart_uploads(ListMultipartUploadsInput(bucket=bucket))
    for upload in uploads.uploads or []:
        client.abort_multipart_upload(
            AbortMultipartUploadInput(
                bucket=bucket, key=upload.key, upload_id=upload.upload_id
            )
        )

    token: str | None = None
    while True:
        page = client.list_objects_v2(
            ListObjectsV2Input(bucket=bucket, continuation_token=token)
        )
        keys = [obj.key for obj in page.contents or [] if obj.key is not None]
        if keys:
            client.delete_objects(
                DeleteObjectsInput(
                    bucket=bucket,
                    delete=Delete(objects=[ObjectIdentifier(key=key) for key in keys]),
                )
            )
        if not page.is_truncated:
            break
        token = page.next_continuation_token

    client.delete_bucket(DeleteBucketInput(bucket=bucket))


@pytest.fixture(scope="session")
def bucket() -> Iterator[str]:
    """A bucket in ``REGION`` shared by every test in the session."""
    name = unique_bucket_name()
    with create_sync_client(ClientOptions()) as client:
        client.create_bucket(
            CreateBucketInput(
                bucket=name, create_bucket_configuration=in_region(REGION)
            )
        )
        try:
            # New buckets block SSE-C uploads by default.
            client.put_bucket_encryption(
                PutBucketEncryptionInput(
                    bucket=name,
                    server_side_encryption_configuration=ServerSideEncryptionConfiguration(
                        rules=[
                            ServerSideEncryptionRule(
                                apply_server_side_encryption_by_default=ServerSideEncryptionByDefault(
                                    sse_algorithm=ServerSideEncryption.AES256
                                ),
                                blocked_encryption_types=BlockedEncryptionTypes(
                                    encryption_type=[EncryptionType.NONE]
                                ),
                            )
                        ]
                    ),
                )
            )
            yield name
        finally:
            empty_and_delete_bucket(client, name)


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def make_s3(mode: Mode) -> AsyncIterator[S3Factory]:
    """Build clients in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:

        async def make(options: ClientOptions) -> AsyncS3Client:
            return await open_client(
                stack,
                mode,
                lambda: create_async_client(options),
                lambda: create_sync_client(options),
            )

        yield make


@pytest.fixture
async def s3(make_s3: S3Factory) -> AsyncS3Client:
    return await make_s3(ClientOptions())
