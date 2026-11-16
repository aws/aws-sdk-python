# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the DynamoDB integration tests.

The session ``table`` runs on the session event loop so it can use the shared
waiters. ``dynamodb`` is parametrized over both client modes.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
import pytest_asyncio
from aws_sdk_dynamodb.aio.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.models import DeleteTableInput
from dual_mode import MODES, Mode, open_client

from . import (
    create_async_client,
    create_sync_client,
    table_input,
    unique_table_name,
    wait_for_active,
)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def table() -> AsyncIterator[str]:
    """An ACTIVE table shared by every test in the session."""
    name = unique_table_name()
    async with await create_async_client() as client:
        await client.create_table(table_input(name))
        try:
            await wait_for_active(client, name)
            yield name
        finally:
            await client.delete_table(DeleteTableInput(table_name=name))


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def dynamodb(mode: Mode) -> AsyncIterator[AsyncDynamoDBClient]:
    """A client in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)
