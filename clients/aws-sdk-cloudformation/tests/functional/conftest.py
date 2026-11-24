# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the mocked CloudFormation tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.aio.config import AsyncCloudFormationConfig
from aws_sdk_cloudformation.client import CloudFormationClient
from aws_sdk_cloudformation.config import CloudFormationConfig
from dual_mode import MODES, AwaitableClient, Mode
from smithy_test import mock
from smithy_test.aio import mock_async

from . import REGION, MockedClient


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def cloudformation(mode: Mode) -> AsyncIterator[MockedClient]:
    """A mocked client in the test's mode; unmet expectations fail the test at teardown."""
    async with AsyncExitStack() as stack:
        if mode == "async":
            config = await AsyncCloudFormationConfig.resolve(region=REGION)
            async_client = AsyncCloudFormationClient(config=config)
            http = await stack.enter_async_context(await mock_async(async_client))
            client = await stack.enter_async_context(async_client)
        else:
            sync_client = CloudFormationClient(
                CloudFormationConfig.resolve(region=REGION)
            )
            http = stack.enter_context(mock(sync_client))
            # Sync and async clients share operation names and models, so the
            # adapter stands in for the async type and pyright checks every call.
            client = cast(
                AsyncCloudFormationClient,
                await stack.enter_async_context(AwaitableClient(sync_client)),
            )
        yield MockedClient(client, http)
