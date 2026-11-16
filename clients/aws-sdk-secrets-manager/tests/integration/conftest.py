# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the Secrets Manager integration tests."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_secrets_manager.aio.client import AsyncSecretsManagerClient
from aws_sdk_secrets_manager.client import SecretsManagerClient
from aws_sdk_secrets_manager.models import (
    CreateSecretInput,
    DeleteSecretInput,
    GetSecretValueInput,
    GetSecretValueOutput,
    ResourceNotFoundException,
    Tag,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until, wait_until_gone

from . import create_async_client, create_sync_client, unique_name

SECRET_VALUE = "first-value"


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def secrets(mode: Mode) -> AsyncIterator[AsyncSecretsManagerClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def secret_name() -> Iterator[str]:
    """A secret holding ``SECRET_VALUE``, force-deleted after the test."""
    name = unique_name()
    with create_sync_client() as client:
        client.create_secret(
            CreateSecretInput(
                name=name,
                secret_string=SECRET_VALUE,
                tags=[Tag(key="Purpose", value="IntegTest")],
            )
        )
        try:
            asyncio.run(
                wait_until(
                    lambda: _get(client, name),
                    retry_on=(ResourceNotFoundException,),
                    interval=2,
                )
            )
            yield name
        finally:
            # Without this the name stays reserved for the recovery window.
            client.delete_secret(
                DeleteSecretInput(secret_id=name, force_delete_without_recovery=True)
            )
            asyncio.run(
                wait_until_gone(
                    lambda: _get(client, name),
                    gone_on=(ResourceNotFoundException,),
                    interval=2,
                )
            )


async def _get(client: SecretsManagerClient, name: str) -> GetSecretValueOutput:
    return client.get_secret_value(GetSecretValueInput(secret_id=name))
