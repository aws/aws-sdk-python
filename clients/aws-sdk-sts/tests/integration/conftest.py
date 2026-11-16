# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the STS integration tests."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_sts.aio.client import AsyncSTSClient
from dual_mode import MODES, Mode, open_client
from smithy_aws_core.identity import AWSCredentialsIdentity

from . import create_async_client, create_sync_client

type STSFactory = Callable[[AWSCredentialsIdentity | None], Awaitable[AsyncSTSClient]]


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def make_sts(mode: Mode) -> AsyncIterator[STSFactory]:
    """Build clients in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:

        async def make(credentials: AWSCredentialsIdentity | None) -> AsyncSTSClient:
            return await open_client(
                stack,
                mode,
                lambda: create_async_client(credentials),
                lambda: create_sync_client(credentials),
            )

        yield make


@pytest.fixture
async def sts(make_sts: STSFactory) -> AsyncSTSClient:
    return await make_sts(None)
