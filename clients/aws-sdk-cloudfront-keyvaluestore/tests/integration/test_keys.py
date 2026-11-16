# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Key lifecycle with ETag/If-Match against a pre-provisioned store."""

import pytest
from aws_sdk_cloudfront_keyvaluestore.aio.client import (
    AsyncCloudFrontKeyValueStoreClient,
)
from aws_sdk_cloudfront_keyvaluestore.models import (
    ConflictException,
    DeleteKeyInput,
    DeleteKeyRequestListItem,
    DescribeKeyValueStoreInput,
    GetKeyInput,
    ListKeysInput,
    PutKeyInput,
    PutKeyRequestListItem,
    ResourceNotFoundException,
    UpdateKeysInput,
)
from waiters import wait_until, wait_until_gone

from . import unique_name


@pytest.mark.skip(
    reason="TODO: the generated client registers only SigV4, and the KeyValueStore endpoint requires SigV4a"
)
async def test_put_get_list_delete_key(
    kvs: AsyncCloudFrontKeyValueStoreClient, kvs_arn: str
) -> None:
    """A key put with the store's ETag is readable and listed, then removed by a delete."""
    key = unique_name()
    etag = (
        await kvs.describe_key_value_store(DescribeKeyValueStoreInput(kvs_arn=kvs_arn))
    ).e_tag
    put = await kvs.put_key(
        PutKeyInput(kvs_arn=kvs_arn, key=key, value="v1", if_match=etag)
    )
    try:
        assert put.e_tag != etag

        got = await wait_until(
            lambda: kvs.get_key(GetKeyInput(kvs_arn=kvs_arn, key=key)),
            retry_on=(ResourceNotFoundException,),
            interval=2,
        )
        assert got.value == "v1"

        listed = await wait_until(
            lambda: kvs.list_keys(ListKeysInput(kvs_arn=kvs_arn)),
            lambda r: (key, "v1") in [(i.key, i.value) for i in r.items or []],
            interval=2,
        )
        assert (key, "v1") in [(i.key, i.value) for i in listed.items or []]
    finally:
        current = await _current_etag(kvs, kvs_arn, put.e_tag)
        await kvs.delete_key(DeleteKeyInput(kvs_arn=kvs_arn, key=key, if_match=current))

    await wait_until_gone(
        lambda: kvs.get_key(GetKeyInput(kvs_arn=kvs_arn, key=key)),
        gone_on=(ResourceNotFoundException,),
        interval=2,
    )
    with pytest.raises(ResourceNotFoundException):
        await kvs.get_key(GetKeyInput(kvs_arn=kvs_arn, key=key))


@pytest.mark.skip(
    reason="TODO: the generated client registers only SigV4, and the KeyValueStore endpoint requires SigV4a"
)
async def test_batch_update_and_stale_etag(
    kvs: AsyncCloudFrontKeyValueStoreClient, kvs_arn: str
) -> None:
    """A batched update applies puts and deletes atomically, and a stale ETag raises ConflictException."""
    keep, drop = unique_name(), unique_name()
    etag = (
        await kvs.describe_key_value_store(DescribeKeyValueStoreInput(kvs_arn=kvs_arn))
    ).e_tag
    first = await kvs.update_keys(
        UpdateKeysInput(
            kvs_arn=kvs_arn,
            if_match=etag,
            puts=[
                PutKeyRequestListItem(key=keep, value="a"),
                PutKeyRequestListItem(key=drop, value="b"),
            ],
        )
    )
    latest = first.e_tag
    try:
        await _current_etag(kvs, kvs_arn, latest)
        with pytest.raises(ConflictException):
            await kvs.update_keys(
                UpdateKeysInput(
                    kvs_arn=kvs_arn,
                    if_match=etag,
                    puts=[PutKeyRequestListItem(key=keep, value="c")],
                )
            )

        second = await kvs.update_keys(
            UpdateKeysInput(
                kvs_arn=kvs_arn,
                if_match=first.e_tag,
                deletes=[DeleteKeyRequestListItem(key=drop)],
            )
        )
        latest = second.e_tag
        assert second.item_count == first.item_count - 1
        got = await wait_until(
            lambda: kvs.get_key(GetKeyInput(kvs_arn=kvs_arn, key=keep)),
            retry_on=(ResourceNotFoundException,),
            interval=2,
        )
        assert got.value == "a"
    finally:
        current = await _current_etag(kvs, kvs_arn, latest)
        await kvs.update_keys(
            UpdateKeysInput(
                kvs_arn=kvs_arn,
                if_match=current,
                deletes=[DeleteKeyRequestListItem(key=keep)],
            )
        )


async def _current_etag(
    kvs: AsyncCloudFrontKeyValueStoreClient, kvs_arn: str, expected: str | None
) -> str:
    """Re-read the store ETag until it reflects the last write, so the next write is not stale."""
    described = await wait_until(
        lambda: kvs.describe_key_value_store(
            DescribeKeyValueStoreInput(kvs_arn=kvs_arn)
        ),
        lambda r: r.e_tag == expected,
        interval=2,
    )
    assert described.e_tag is not None
    return described.e_tag
