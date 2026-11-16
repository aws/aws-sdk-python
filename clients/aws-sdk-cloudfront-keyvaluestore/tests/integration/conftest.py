# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the CloudFront KeyValueStore integration tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_cloudfront_keyvaluestore.aio.client import (
    AsyncCloudFrontKeyValueStoreClient,
)
from dual_mode import MODES, Mode, open_client

from . import STORE_ARN_ENV, create_async_client, create_sync_client, store_arn


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def kvs(mode: Mode) -> AsyncIterator[AsyncCloudFrontKeyValueStoreClient]:
    """A client in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def kvs_arn() -> str:
    """The ARN of an empty, pre-provisioned store the tests may modify."""
    arn = store_arn()
    if arn is None:
        pytest.skip(f"{STORE_ARN_ENV} is not set")
    return arn
