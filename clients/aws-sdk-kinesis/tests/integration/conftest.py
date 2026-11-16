# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the Kinesis integration tests.

The session ``stream`` is created and torn down with the sync client, so it
never depends on an event loop. ``kinesis`` is parametrized over both client
modes.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_kinesis.aio.client import AsyncKinesisClient
from aws_sdk_kinesis.client import KinesisClient
from aws_sdk_kinesis.models import (
    CreateStreamInput,
    DeleteStreamInput,
    DescribeStreamSummaryInput,
    DescribeStreamSummaryOutput,
    ListShardsInput,
    ListShardsOutput,
    ResourceInUseException,
    ResourceNotFoundException,
    StreamMode,
    StreamModeDetails,
    StreamStatus,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until, wait_until_gone

from . import create_async_client, create_sync_client, unique_stream_name

# Create and delete take tens of seconds.
SLOW_TIMEOUT_SECONDS = 300


@pytest.fixture(scope="session")
def stream() -> Iterator[str]:
    """An on-demand stream, ACTIVE, shared by every test in the session."""
    name = unique_stream_name()
    with create_sync_client() as client:
        client.create_stream(
            CreateStreamInput(
                stream_name=name,
                stream_mode_details=StreamModeDetails(stream_mode=StreamMode.ON_DEMAND),
                tags={"Purpose": "IntegTest"},
            )
        )
        try:
            asyncio.run(_wait_until_active_with_shards(client, name))
            yield name
        finally:
            client.delete_stream(
                DeleteStreamInput(stream_name=name, enforce_consumer_deletion=True)
            )
            asyncio.run(_wait_until_deleted(client, name))


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def kinesis(mode: Mode) -> AsyncIterator[AsyncKinesisClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


async def _wait_until_active_with_shards(client: KinesisClient, name: str) -> None:
    await wait_until(
        lambda: _describe(client, name),
        done=lambda r: (
            r.stream_description_summary.stream_status == StreamStatus.ACTIVE
        ),
        retry_on=(ResourceNotFoundException,),
        interval=2,
        timeout=SLOW_TIMEOUT_SECONDS,
    )
    await wait_until(
        lambda: _list_shards(client, name),
        done=lambda r: len(r.shards or []) > 1,
        retry_on=(ResourceNotFoundException, ResourceInUseException),
        interval=2,
        timeout=SLOW_TIMEOUT_SECONDS,
    )


async def _wait_until_deleted(client: KinesisClient, name: str) -> None:
    await wait_until_gone(
        lambda: _describe(client, name),
        gone_on=(ResourceNotFoundException,),
        interval=5,
        timeout=SLOW_TIMEOUT_SECONDS,
    )


async def _describe(client: KinesisClient, name: str) -> DescribeStreamSummaryOutput:
    return client.describe_stream_summary(DescribeStreamSummaryInput(stream_name=name))


async def _list_shards(client: KinesisClient, name: str) -> ListShardsOutput:
    return client.list_shards(ListShardsInput(stream_name=name))
