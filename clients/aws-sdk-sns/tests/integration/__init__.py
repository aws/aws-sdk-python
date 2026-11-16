# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live SNS integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_sns.aio.client import AsyncSNSClient
from aws_sdk_sns.aio.config import AsyncSNSConfig
from aws_sdk_sns.client import SNSClient
from aws_sdk_sns.config import SNSConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
TOPIC_PREFIX = "aws-sdk-python-integ-"


def unique_topic_name(infix: str = "") -> str:
    return f"{TOPIC_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncSNSClient:
    config = await AsyncSNSConfig.resolve(region=REGION)
    return AsyncSNSClient(config=config)


def create_sync_client() -> SNSClient:
    config = SNSConfig.resolve(region=REGION)
    return SNSClient(config=config)
