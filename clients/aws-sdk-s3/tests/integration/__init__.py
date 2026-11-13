# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live S3 integration tests, written once and run in both sync and async modes."""

import uuid
from dataclasses import dataclass
from typing import Any

from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.aio.config import AsyncS3Config
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import BucketLocationConstraint, CreateBucketConfiguration
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_aws_core.identity import EnvironmentCredentialsResolver
from smithy_core.aio.interfaces import StreamingBlob
from smithy_core.aio.utils import read_streaming_blob_async
from smithy_core.interceptors import Interceptor

REGION = "us-west-2"
OTHER_REGION = "us-east-2"

# Lets an interrupted run's leftovers be found and removed.
BUCKET_PREFIX = "aws-sdk-python-integ-"


def unique_bucket_name(infix: str = "") -> str:
    return f"{BUCKET_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


@dataclass(frozen=True, kw_only=True)
class ClientOptions:
    """Mode-neutral client settings, applied to either client's config."""

    region: str = REGION
    force_path_style: bool | None = None
    use_accelerate_endpoint: bool | None = None
    interceptors: tuple[Interceptor[Any, Any, Any, Any], ...] = ()


async def create_async_client(options: ClientOptions) -> AsyncS3Client:
    config = await AsyncS3Config.resolve(
        region=options.region,
        aws_credentials_identity_resolver=AsyncEnvironmentCredentialsResolver(),
        force_path_style=options.force_path_style,
        use_accelerate_endpoint=options.use_accelerate_endpoint,
        interceptors=list(options.interceptors),
    )
    return AsyncS3Client(config=config)


def create_sync_client(options: ClientOptions) -> S3Client:
    config = S3Config.resolve(
        region=options.region,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        force_path_style=options.force_path_style,
        use_accelerate_endpoint=options.use_accelerate_endpoint,
        interceptors=list(options.interceptors),
    )
    return S3Client(config=config)


def in_region(region: str) -> CreateBucketConfiguration:
    """The bucket configuration CreateBucket needs outside us-east-1."""
    return CreateBucketConfiguration(
        location_constraint=BucketLocationConstraint(region)
    )


async def read_body(body: StreamingBlob) -> bytes:
    """Read a response body from either client."""
    return await read_streaming_blob_async(body)
