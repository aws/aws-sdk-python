# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Bucket addressing styles, from JS v3 s3-bucket-features.e2e and S3.spec."""

from collections.abc import Awaitable, Callable

import pytest
from aws_sdk_s3.models import (
    AccelerateConfiguration,
    BucketAccelerateStatus,
    CreateBucketInput,
    DeleteBucketInput,
    DeleteObjectInput,
    GetObjectInput,
    HeadBucketInput,
    NoSuchBucket,
    NotFound,
    PutBucketAccelerateConfigurationInput,
    PutObjectInput,
)
from dual_mode import RequestRecorder
from smithy_core.exceptions import CallError
from waiters import wait_until, wait_until_gone

from . import REGION, ClientOptions, in_region, read_body, unique_bucket_name
from .conftest import S3Factory

KEY = "addressing.txt"
BODY = b"addressing"
ACCELERATE_TIMEOUT = 120


async def test_virtual_hosted_style_by_default(make_s3: S3Factory, bucket: str) -> None:
    recorder = RequestRecorder()
    s3 = await make_s3(ClientOptions(interceptors=(recorder,)))
    await s3.put_object(PutObjectInput(bucket=bucket, key=KEY, body=BODY))

    destination = recorder.requests[-1].destination
    assert destination.host == f"{bucket}.s3.{REGION}.amazonaws.com"
    assert destination.path == f"/{KEY}"


async def test_force_path_style(make_s3: S3Factory, bucket: str) -> None:
    recorder = RequestRecorder()
    s3 = await make_s3(ClientOptions(force_path_style=True, interceptors=(recorder,)))
    await s3.put_object(PutObjectInput(bucket=bucket, key=KEY, body=BODY))
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=KEY))
    assert await read_body(output.body) == BODY

    destination = recorder.requests[-1].destination
    assert destination.host == f"s3.{REGION}.amazonaws.com"
    assert destination.path == f"/{bucket}/{KEY}"


async def test_dotted_bucket_name_uses_path_style(make_s3: S3Factory) -> None:
    # TLS certificates don't cover dots in the bucket label, so the endpoint
    # rules fall back to path-style addressing.
    recorder = RequestRecorder()
    s3 = await make_s3(ClientOptions(interceptors=(recorder,)))
    name = unique_bucket_name("dotted.")
    await s3.create_bucket(
        CreateBucketInput(bucket=name, create_bucket_configuration=in_region(REGION))
    )
    try:
        await wait_until(
            lambda: s3.head_bucket(HeadBucketInput(bucket=name)),
            retry_on=(NotFound, NoSuchBucket),
            interval=2,
        )
        await s3.put_object(PutObjectInput(bucket=name, key=KEY, body=BODY))
        output = await s3.get_object(GetObjectInput(bucket=name, key=KEY))
        assert await read_body(output.body) == BODY
        assert recorder.requests[-1].destination.path == f"/{name}/{KEY}"
    finally:
        await s3.delete_object(DeleteObjectInput(bucket=name, key=KEY))
        await s3.delete_bucket(DeleteBucketInput(bucket=name))
        await wait_until_gone(
            lambda: s3.head_bucket(HeadBucketInput(bucket=name)),
            gone_on=(NotFound, NoSuchBucket),
            interval=2,
        )


async def test_accelerate_endpoint(make_s3: S3Factory, bucket: str) -> None:
    s3 = await make_s3(ClientOptions())
    await s3.put_bucket_accelerate_configuration(
        PutBucketAccelerateConfigurationInput(
            bucket=bucket,
            accelerate_configuration=AccelerateConfiguration(
                status=BucketAccelerateStatus.ENABLED
            ),
        )
    )

    recorder = RequestRecorder()
    accelerated = await make_s3(
        ClientOptions(use_accelerate_endpoint=True, interceptors=(recorder,))
    )
    # Acceleration takes a while to activate, and until then the accelerate
    # endpoint answers with a 307.
    await wait_until(
        _until_accelerated(
            lambda: accelerated.put_object(
                PutObjectInput(bucket=bucket, key=KEY, body=BODY)
            )
        ),
        retry_on=(_AccelerationPending,),
        interval=5,
        timeout=ACCELERATE_TIMEOUT,
    )
    assert recorder.requests[-1].destination.host == (
        f"{bucket}.s3-accelerate.amazonaws.com"
    )


@pytest.mark.skip(
    reason="SigV4a signing for Multi-Region Access Points is not implemented."
)
async def test_multi_region_access_point() -> None: ...


class _AccelerationPending(Exception):
    """The accelerate endpoint still answers with a 307."""


def _until_accelerated[T](
    read: Callable[[], Awaitable[T]],
) -> Callable[[], Awaitable[T]]:
    async def wrapped() -> T:
        try:
            return await read()
        except CallError as error:
            if error.response_metadata.http_status_code == 307:
                raise _AccelerationPending() from error
            raise

    return wrapped
