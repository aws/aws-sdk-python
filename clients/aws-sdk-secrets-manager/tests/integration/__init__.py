# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live Secrets Manager integration tests, run in both sync and async modes."""

import uuid

from aws_sdk_secrets_manager.aio.client import AsyncSecretsManagerClient
from aws_sdk_secrets_manager.aio.config import AsyncSecretsManagerConfig
from aws_sdk_secrets_manager.client import SecretsManagerClient
from aws_sdk_secrets_manager.config import SecretsManagerConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_name() -> str:
    return f"{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncSecretsManagerClient:
    config = await AsyncSecretsManagerConfig.resolve(region=REGION)
    return AsyncSecretsManagerClient(config=config)


def create_sync_client() -> SecretsManagerClient:
    config = SecretsManagerConfig.resolve(region=REGION)
    return SecretsManagerClient(config=config)
