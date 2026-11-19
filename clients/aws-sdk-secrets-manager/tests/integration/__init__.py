# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live Secrets Manager integration tests, run in both sync and async modes."""

import uuid
from collections.abc import Awaitable, Callable

from aws_sdk_secrets_manager.aio.client import AsyncSecretsManagerClient
from aws_sdk_secrets_manager.aio.config import AsyncSecretsManagerConfig
from aws_sdk_secrets_manager.client import SecretsManagerClient
from aws_sdk_secrets_manager.config import SecretsManagerConfig
from aws_sdk_secrets_manager.models import (
    InvalidRequestException,
    ResourceNotFoundException,
)
from waiters import wait_until

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


async def wait_until_secret_deleted(read: Callable[[], Awaitable[object]]) -> None:
    """Polls ``read`` until it raises ResourceNotFoundException, riding out the in-progress deletion error."""

    async def is_gone() -> bool:
        try:
            await read()
        except ResourceNotFoundException:
            return True
        return False

    # A secret being deleted raises InvalidRequestException until the deletion settles.
    await wait_until(
        is_gone, lambda gone: gone, retry_on=(InvalidRequestException,), interval=2
    )
