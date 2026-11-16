# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the CloudFront integration tests."""

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_cloudfront.aio.client import AsyncCloudFrontClient
from aws_sdk_cloudfront.models import (
    CreateCachePolicyInput,
    DeleteCachePolicyInput,
    GetCachePolicyInput,
    NoSuchCachePolicy,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until

from . import cache_policy_config, create_async_client, create_sync_client, unique_name


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def cloudfront(mode: Mode) -> AsyncIterator[AsyncCloudFrontClient]:
    """A client in the test's mode, closed when the test ends."""
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def cache_policy_ids() -> Iterator[list[str]]:
    """Cache policy IDs a test appends to are deleted at teardown, even after failures."""
    ids: list[str] = []
    try:
        yield ids
    finally:
        with create_sync_client() as client:
            for policy_id in ids:
                # Tests that delete their own policy leave nothing to clean up, and
                # updates change the ETag, so read it fresh.
                try:
                    current = client.get_cache_policy(GetCachePolicyInput(id=policy_id))
                except NoSuchCachePolicy:
                    continue
                client.delete_cache_policy(
                    DeleteCachePolicyInput(id=policy_id, if_match=current.e_tag)
                )


@pytest.fixture
def make_cache_policy(
    cloudfront: AsyncCloudFrontClient, cache_policy_ids: list[str]
) -> Callable[[], Awaitable[tuple[str, str, str]]]:
    """Create a cache policy, returning its ID, name and ETag; deleted at teardown."""

    async def make() -> tuple[str, str, str]:
        name = unique_name()
        created = await cloudfront.create_cache_policy(
            CreateCachePolicyInput(cache_policy_config=cache_policy_config(name))
        )
        assert created.cache_policy is not None
        assert created.e_tag is not None
        cache_policy_ids.append(created.cache_policy.id)
        policy_id = created.cache_policy.id
        await wait_until(
            lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
            retry_on=(NoSuchCachePolicy,),
            interval=2,
        )
        return created.cache_policy.id, name, created.e_tag

    return make
