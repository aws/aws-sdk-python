# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live KMS integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_kms.aio.client import AsyncKMSClient
from aws_sdk_kms.aio.config import AsyncKMSConfig
from aws_sdk_kms.client import KMSClient
from aws_sdk_kms.config import KMSConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_alias_name() -> str:
    return f"alias/{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncKMSClient:
    config = await AsyncKMSConfig.resolve(region=REGION)
    return AsyncKMSClient(config=config)


def create_sync_client() -> KMSClient:
    config = KMSConfig.resolve(region=REGION)
    return KMSClient(config=config)
