# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the CloudFormation integration tests."""

from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.models import DeleteStackInput
from dual_mode import MODES, Mode, open_client

from . import create_async_client, create_sync_client


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def cloudformation(mode: Mode) -> AsyncIterator[AsyncCloudFormationClient]:
    """A client in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def created_stacks() -> Iterator[list[str]]:
    """Stack IDs a test appends to are deleted at teardown, even after failures."""
    ids: list[str] = []
    try:
        yield ids
    finally:
        with create_sync_client() as client:
            for stack_id in ids:
                client.delete_stack(DeleteStackInput(stack_name=stack_id))
