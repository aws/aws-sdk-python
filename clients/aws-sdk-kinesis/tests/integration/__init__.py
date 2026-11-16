# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live Kinesis integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_kinesis.aio.client import AsyncKinesisClient
from aws_sdk_kinesis.aio.config import AsyncKinesisConfig
from aws_sdk_kinesis.client import KinesisClient
from aws_sdk_kinesis.config import KinesisConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
STREAM_PREFIX = "aws-sdk-python-integ-"


def unique_stream_name() -> str:
    return f"{STREAM_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncKinesisClient:
    config = await AsyncKinesisConfig.resolve(region=REGION)
    return AsyncKinesisClient(config=config)


def create_sync_client() -> KinesisClient:
    config = KinesisConfig.resolve(region=REGION)
    return KinesisClient(config=config)
