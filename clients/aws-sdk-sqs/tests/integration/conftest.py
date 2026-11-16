# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the SQS integration tests.

Queues are created and deleted with the async client so the shared waiters can
confirm they resolve. ``sqs`` is parametrized over both client modes.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_sqs.aio.client import AsyncSQSClient
from aws_sdk_sqs.models import (
    CreateQueueInput,
    DeleteQueueInput,
    GetQueueUrlInput,
    QueueDoesNotExist,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until

from . import create_async_client, create_sync_client, unique_queue_name

type QueueFactory = Callable[..., Awaitable[str]]


@pytest.fixture
async def make_queue() -> AsyncIterator[QueueFactory]:
    """Create tagged queues that resolve by name, all deleted when the test ends."""
    urls: list[str] = []
    async with await create_async_client() as client:

        async def make(
            name: str | None = None, attributes: dict[str, str] | None = None
        ) -> str:
            queue_name = name or unique_queue_name()
            output = await client.create_queue(
                CreateQueueInput(
                    queue_name=queue_name,
                    attributes=attributes,
                    tags={"Purpose": "IntegTest"},
                )
            )
            assert output.queue_url is not None
            urls.append(output.queue_url)
            await wait_until(
                lambda: client.get_queue_url(GetQueueUrlInput(queue_name=queue_name)),
                retry_on=(QueueDoesNotExist,),
                interval=2,
            )
            return output.queue_url

        try:
            yield make
        finally:
            for url in urls:
                await client.delete_queue(DeleteQueueInput(queue_url=url))


@pytest.fixture
async def queue_url(make_queue: QueueFactory) -> str:
    return await make_queue()


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def sqs(mode: Mode) -> AsyncIterator[AsyncSQSClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)
