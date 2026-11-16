# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Cache policy lifecycle with ETag/If-Match, and listing, from JS v3 cloudfront-features.e2e."""

from collections.abc import Awaitable, Callable

import pytest
from aws_sdk_cloudfront.aio.client import AsyncCloudFrontClient
from aws_sdk_cloudfront.models import (
    CachePolicyType,
    DeleteCachePolicyInput,
    GetCachePolicyInput,
    ListCachePoliciesInput,
    ListDistributionsInput,
    NoSuchCachePolicy,
    PreconditionFailed,
    UpdateCachePolicyInput,
)
from waiters import wait_until, wait_until_gone

from . import cache_policy_config

type PolicyFactory = Callable[[], Awaitable[tuple[str, str, str]]]


@pytest.mark.skip(
    reason="TODO: CloudFront throttles (400 Throttling, Rate exceeded) back-to-back cache policy writes, so this fails intermittently"
)
async def test_cache_policy_lifecycle(
    cloudfront: AsyncCloudFrontClient, make_cache_policy: PolicyFactory
) -> None:
    """A cache policy is created, read back, updated with its ETag, and deleted."""
    policy_id, name, etag = await make_cache_policy()

    fetched = await wait_until(
        lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
        lambda r: r.e_tag == etag,
        retry_on=(NoSuchCachePolicy,),
        interval=2,
    )
    assert fetched.e_tag == etag
    assert fetched.cache_policy is not None
    assert fetched.cache_policy.cache_policy_config.name == name
    assert fetched.cache_policy.cache_policy_config.default_ttl == 60

    updated = await cloudfront.update_cache_policy(
        UpdateCachePolicyInput(
            id=policy_id,
            if_match=etag,
            cache_policy_config=cache_policy_config(name, default_ttl=120),
        )
    )
    assert updated.cache_policy is not None
    assert updated.cache_policy.cache_policy_config.default_ttl == 120
    assert updated.e_tag is not None
    assert updated.e_tag != etag

    # The delete needs the post-update ETag, which a lagging read can still show as the old one.
    current = await wait_until(
        lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
        lambda r: r.e_tag == updated.e_tag,
        retry_on=(NoSuchCachePolicy,),
        interval=2,
    )
    await cloudfront.delete_cache_policy(
        DeleteCachePolicyInput(id=policy_id, if_match=current.e_tag)
    )
    await wait_until_gone(
        lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
        gone_on=(NoSuchCachePolicy,),
        interval=2,
    )
    with pytest.raises(NoSuchCachePolicy):
        await cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id))


@pytest.mark.skip(
    reason="TODO: CloudFront throttles (400 Throttling, Rate exceeded) back-to-back cache policy writes, so this fails intermittently"
)
async def test_stale_etag_is_rejected_after_update(
    cloudfront: AsyncCloudFrontClient, make_cache_policy: PolicyFactory
) -> None:
    """Updating with the ETag from before a prior update raises PreconditionFailed and changes nothing."""
    policy_id, name, stale_etag = await make_cache_policy()
    await cloudfront.update_cache_policy(
        UpdateCachePolicyInput(
            id=policy_id,
            if_match=stale_etag,
            cache_policy_config=cache_policy_config(name, default_ttl=120),
        )
    )
    await wait_until(
        lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
        lambda r: r.e_tag != stale_etag,
        retry_on=(NoSuchCachePolicy,),
        interval=2,
    )

    with pytest.raises(PreconditionFailed):
        await cloudfront.update_cache_policy(
            UpdateCachePolicyInput(
                id=policy_id,
                if_match=stale_etag,
                cache_policy_config=cache_policy_config(name, default_ttl=240),
            )
        )

    current = await wait_until(
        lambda: cloudfront.get_cache_policy(GetCachePolicyInput(id=policy_id)),
        lambda r: r.e_tag != stale_etag,
        retry_on=(NoSuchCachePolicy,),
        interval=2,
    )
    assert current.cache_policy is not None
    assert current.cache_policy.cache_policy_config.default_ttl == 120


@pytest.mark.skip(
    reason="TODO: CloudFront throttles (400 Throttling, Rate exceeded) back-to-back cache policy writes, so this fails intermittently"
)
async def test_list_custom_cache_policies_paginates_with_marker(
    cloudfront: AsyncCloudFrontClient, make_cache_policy: PolicyFactory
) -> None:
    """Listing custom policies one per page by marker visits every policy this test created."""
    created = {(await make_cache_policy())[0] for _ in range(2)}

    seen = await wait_until(
        lambda: _list_custom_policy_ids(cloudfront),
        lambda ids: created <= ids,
        interval=2,
    )

    assert created <= seen


async def test_list_distributions_returns_a_count(
    cloudfront: AsyncCloudFrontClient,
) -> None:
    """ListDistributions succeeds with the configured credentials and reports a quantity."""
    result = await cloudfront.list_distributions(ListDistributionsInput())
    assert result.distribution_list is not None
    assert result.distribution_list.quantity >= 0


async def _list_custom_policy_ids(cloudfront: AsyncCloudFrontClient) -> set[str]:
    seen: set[str] = set()
    marker: str | None = None
    for _ in range(1000):
        page = await cloudfront.list_cache_policies(
            ListCachePoliciesInput(
                type=CachePolicyType.CUSTOM, max_items=1, marker=marker
            )
        )
        assert page.cache_policy_list is not None
        assert len(page.cache_policy_list.items or []) <= 1
        seen.update(item.cache_policy.id for item in page.cache_policy_list.items or [])
        marker = page.cache_policy_list.next_marker
        if marker is None:
            return seen
    pytest.fail("pagination did not terminate")
