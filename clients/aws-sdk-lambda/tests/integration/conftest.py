# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the Lambda integration tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_lambda.aio.client import AsyncLambdaClient
from dual_mode import MODES, Mode, open_client

from . import create_async_client, create_sync_client


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def lambda_client(mode: Mode) -> AsyncIterator[AsyncLambdaClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)
