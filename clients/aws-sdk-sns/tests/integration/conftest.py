# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the SNS integration tests.

Topics are created and deleted with the sync client, so they never depend on
an event loop. ``sns`` is parametrized over both client modes.
"""

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_sns.aio.client import AsyncSNSClient
from aws_sdk_sns.models import CreateTopicInput, DeleteTopicInput, Tag
from dual_mode import MODES, Mode, open_client

from . import create_async_client, create_sync_client, unique_topic_name

type TopicFactory = Callable[..., str]


@pytest.fixture
def make_topic() -> Iterator[TopicFactory]:
    """Create tagged topics, all deleted when the test ends."""
    arns: list[str] = []
    with create_sync_client() as client:

        def make(tags: list[Tag] | None = None) -> str:
            output = client.create_topic(
                CreateTopicInput(
                    name=unique_topic_name(),
                    tags=[Tag(key="Purpose", value="IntegTest"), *(tags or [])],
                )
            )
            assert output.topic_arn is not None
            arns.append(output.topic_arn)
            return output.topic_arn

        try:
            yield make
        finally:
            for arn in arns:
                client.delete_topic(DeleteTopicInput(topic_arn=arn))


@pytest.fixture
def topic_arn(make_topic: TopicFactory) -> str:
    return make_topic()


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def sns(mode: Mode) -> AsyncIterator[AsyncSNSClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)
