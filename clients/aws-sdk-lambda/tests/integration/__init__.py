# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live Lambda integration tests, run in both sync and async modes."""

import uuid

from aws_sdk_lambda.aio.client import AsyncLambdaClient
from aws_sdk_lambda.aio.config import AsyncLambdaConfig
from aws_sdk_lambda.client import LambdaClient
from aws_sdk_lambda.config import LambdaConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_name() -> str:
    return f"{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncLambdaClient:
    config = await AsyncLambdaConfig.resolve(region=REGION)
    return AsyncLambdaClient(config=config)


def create_sync_client() -> LambdaClient:
    config = LambdaConfig.resolve(region=REGION)
    return LambdaClient(config=config)
