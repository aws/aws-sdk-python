# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live IAM integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_iam.aio.client import AsyncIAMClient
from aws_sdk_iam.aio.config import AsyncIAMConfig
from aws_sdk_iam.client import IAMClient
from aws_sdk_iam.config import IAMConfig
from aws_sdk_iam.models import Tag

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"

INTEG_TAG = Tag(key="Purpose", value="IntegTest")


def unique_name(infix: str = "") -> str:
    return f"{NAME_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncIAMClient:
    config = await AsyncIAMConfig.resolve(region=REGION)
    return AsyncIAMClient(config=config)


def create_sync_client() -> IAMClient:
    config = IAMConfig.resolve(region=REGION)
    return IAMClient(config=config)
