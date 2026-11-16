# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live CloudFront KeyValueStore integration tests, written once and run in both sync and async modes."""

import os
import uuid

from aws_sdk_cloudfront_keyvaluestore.aio.client import (
    AsyncCloudFrontKeyValueStoreClient,
)
from aws_sdk_cloudfront_keyvaluestore.aio.config import (
    AsyncCloudFrontKeyValueStoreConfig,
)
from aws_sdk_cloudfront_keyvaluestore.client import CloudFrontKeyValueStoreClient
from aws_sdk_cloudfront_keyvaluestore.config import CloudFrontKeyValueStoreConfig

REGION = "us-west-2"

# The store is pre-provisioned because creating one needs the CloudFront client,
# which is not a dependency of this package's tests.
STORE_ARN_ENV = "AWS_SDK_PYTHON_INTEG_KVS_ARN"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def store_arn() -> str | None:
    return os.environ.get(STORE_ARN_ENV)


def unique_name() -> str:
    return f"{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncCloudFrontKeyValueStoreClient:
    config = await AsyncCloudFrontKeyValueStoreConfig.resolve(region=REGION)
    return AsyncCloudFrontKeyValueStoreClient(config=config)


def create_sync_client() -> CloudFrontKeyValueStoreClient:
    config = CloudFrontKeyValueStoreConfig.resolve(region=REGION)
    return CloudFrontKeyValueStoreClient(config=config)
