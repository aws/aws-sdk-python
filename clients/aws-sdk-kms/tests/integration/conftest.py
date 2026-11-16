# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the KMS integration tests.

The session ``key`` is created and torn down with the sync client, so it
never depends on an event loop. ``kms`` is parametrized over both client modes.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_kms.aio.client import AsyncKMSClient
from aws_sdk_kms.client import KMSClient
from aws_sdk_kms.models import (
    CreateKeyInput,
    DescribeKeyInput,
    DescribeKeyOutput,
    KeyState,
    KeyUsageType,
    NotFoundException,
    ScheduleKeyDeletionInput,
    Tag,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until

from . import create_async_client, create_sync_client

# The minimum KMS allows.
DELETION_WINDOW_DAYS = 7


@pytest.fixture(scope="session")
def key_id() -> Iterator[str]:
    """A symmetric encryption key shared by every test, scheduled for deletion at teardown."""
    with create_sync_client() as client:
        created = client.create_key(
            CreateKeyInput(
                description="aws-sdk-python integration tests",
                key_usage=KeyUsageType.ENCRYPT_DECRYPT,
                tags=[Tag(tag_key="Purpose", tag_value="IntegTest")],
            )
        )
        assert created.key_metadata is not None
        key = created.key_metadata.key_id

        async def enabled() -> bool:
            described = await wait_until(
                lambda: _describe(client, key),
                done=lambda r: (
                    r.key_metadata is not None
                    and r.key_metadata.key_state == KeyState.ENABLED
                ),
                retry_on=(NotFoundException,),
                interval=2,
            )
            return described.key_metadata is not None

        assert asyncio.run(enabled())
        try:
            yield key
        finally:
            client.schedule_key_deletion(
                ScheduleKeyDeletionInput(
                    key_id=key, pending_window_in_days=DELETION_WINDOW_DAYS
                )
            )


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def kms(mode: Mode) -> AsyncIterator[AsyncKMSClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


async def _describe(client: KMSClient, key: str) -> DescribeKeyOutput:
    return client.describe_key(DescribeKeyInput(key_id=key))
