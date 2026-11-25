# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Bucket and object CRUD, replayed from recordings of the live service.

Record against AWS with ``SMITHY_PYTHON_TEST_MODE=record pytest <this file>``.

The recordings are in ``recordings/<test function>/<client>.py``. One recording serves
both clients, because playback answers by operation and never looks at the request.
Recording runs both clients, and the later run overwrites the recording.

The bucket is in the account regional namespace, which only the account can create
buckets in, so nobody else can take the name. Its name contains the account ID, which
a recorded STS call provides, so the ID is never in the repository.
"""

from contextlib import AsyncExitStack
from typing import cast
from uuid import uuid4

import pytest
from aws_sdk_s3.aio import AsyncS3Client, AsyncS3Config
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_sts.client import STSClient
from aws_sdk_sts.config import STSConfig
from dual_mode import MODES, AwaitableClient, Mode
from smithy_core.aio.utils import read_streaming_blob_async
from smithy_test import instrument
from smithy_test.aio import instrument_async

REGION = "us-west-2"


@pytest.mark.parametrize("mode", MODES)
async def test_bucket_and_object_crud(mode: Mode) -> None:
    sts = STSClient(STSConfig.resolve(region=REGION))
    with sts, instrument(sts):
        account = sts.get_caller_identity().account
    assert account
    bucket = f"aws-sdk-python-recorded-{uuid4().hex[:8]}-{account}-{REGION}-an"

    async with AsyncExitStack() as stack:
        if mode == "async":
            client = AsyncS3Client(await AsyncS3Config.resolve(region=REGION))
            await stack.enter_async_context(client)
            await stack.enter_async_context(
                await instrument_async(client, redact=[account])
            )
            s3 = client
        else:
            sync = S3Client(S3Config.resolve(region=REGION))
            stack.enter_context(instrument(sync, redact=[account]))
            adapter = await stack.enter_async_context(AwaitableClient(sync))
            s3 = cast(AsyncS3Client, adapter)

        await s3.create_bucket(
            bucket=bucket,
            create_bucket_configuration={"location_constraint": REGION},
            bucket_namespace="account-regional",
        )
        try:
            await s3.head_bucket(bucket=bucket)

            await s3.put_object(
                bucket=bucket, key="a/1.txt", body=b"hello", metadata={"k": "v"}
            )
            got = await s3.get_object(bucket=bucket, key="a/1.txt")
            assert await read_streaming_blob_async(got.body) == b"hello"
            assert got.metadata == {"k": "v"}

            head = await s3.head_object(bucket=bucket, key="a/1.txt")
            assert head.content_length == 5

            await s3.copy_object(
                bucket=bucket, key="a/2.txt", copy_source=f"{bucket}/a/1.txt"
            )
            listed = await s3.list_objects_v2(bucket=bucket, prefix="a/")
            assert [o.key for o in listed.contents or []] == ["a/1.txt", "a/2.txt"]

            await s3.delete_objects(
                bucket=bucket,
                delete={"objects": [{"key": "a/1.txt"}, {"key": "a/2.txt"}]},
            )
            listed = await s3.list_objects_v2(bucket=bucket)
            assert not listed.contents
        finally:
            await s3.delete_bucket(bucket=bucket)
