# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Item operations, from JS v3 dynamodb-features.e2e and DynamoDB.e2e."""

import uuid

import pytest
from aws_sdk_dynamodb.aio.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.models import (
    AttributeValue,
    AttributeValueB,
    AttributeValueBOOL,
    AttributeValueBS,
    AttributeValueL,
    AttributeValueM,
    AttributeValueN,
    AttributeValueNS,
    AttributeValueNULL,
    AttributeValueS,
    AttributeValueSS,
    BatchGetItemInput,
    BatchWriteItemInput,
    ConditionalCheckFailedException,
    DeleteItemInput,
    DeleteRequest,
    GetItemInput,
    KeysAndAttributes,
    PutItemInput,
    PutRequest,
    QueryInput,
    ReturnValue,
    ReturnValuesOnConditionCheckFailure,
    ScanInput,
    WriteRequest,
)

from . import HASH_KEY, RANGE_KEY

type Item = dict[str, AttributeValue]


async def test_nested_binary_and_set_attributes_round_trip(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies every attribute type, nested in maps and lists, comes back unchanged."""
    item: Item = {
        HASH_KEY: AttributeValueS(_unique("nested-")),
        RANGE_KEY: AttributeValueS("bår"),
        "data": AttributeValueM(
            {
                "attr1": AttributeValueL(
                    [
                        AttributeValueS("value1"),
                        AttributeValueL(
                            [AttributeValueM({"attr12": AttributeValueS("value2")})]
                        ),
                    ]
                ),
                "attr2": AttributeValueL(
                    [
                        AttributeValueB(b"\x00"),
                        AttributeValueB(b"\x01\xff"),
                        AttributeValueNULL(True),
                        AttributeValueBOOL(True),
                        AttributeValueN("-12500"),
                    ]
                ),
            }
        ),
        "strings": AttributeValueSS(["a", "b", "ü"]),
        "numbers": AttributeValueNS(["1", "2.5", "-3"]),
        "blobs": AttributeValueBS([b"\x00\x01", b"\xfe\xff"]),
    }
    await dynamodb.put_item(PutItemInput(table_name=table, item=item))

    got = await dynamodb.get_item(
        GetItemInput(table_name=table, key=_key(item), consistent_read=True)
    )

    assert got.item is not None
    assert got.item[HASH_KEY] == item[HASH_KEY]
    assert got.item["data"] == item["data"]
    for name in ("strings", "numbers", "blobs"):
        assert _set_members(got.item[name]) == _set_members(item[name])


async def test_item_lifecycle_overwrite_and_delete(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies put, overwrite returning the old item, delete, and a get of the gone item."""
    key: Item = {
        HASH_KEY: AttributeValueS(_unique("life-")),
        RANGE_KEY: AttributeValueS("a"),
    }
    await dynamodb.put_item(
        PutItemInput(table_name=table, item={**key, "v": AttributeValueN("1")})
    )

    overwritten = await dynamodb.put_item(
        PutItemInput(
            table_name=table,
            item={**key, "v": AttributeValueN("2")},
            return_values=ReturnValue.ALL_OLD,
        )
    )
    assert overwritten.attributes is not None
    assert overwritten.attributes["v"] == AttributeValueN("1")

    deleted = await dynamodb.delete_item(
        DeleteItemInput(table_name=table, key=key, return_values=ReturnValue.ALL_OLD)
    )
    assert deleted.attributes is not None
    assert deleted.attributes["v"] == AttributeValueN("2")

    after = await dynamodb.get_item(
        GetItemInput(table_name=table, key=key, consistent_read=True)
    )
    assert after.item is None


async def test_conditional_put_failure_returns_existing_item(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies a put guarded by attribute_not_exists fails with the stored item attached."""
    key: Item = {
        HASH_KEY: AttributeValueS(_unique("cond-")),
        RANGE_KEY: AttributeValueS("a"),
    }
    await dynamodb.put_item(
        PutItemInput(
            table_name=table,
            item={**key, "owner": AttributeValueS("first")},
            condition_expression="attribute_not_exists(#pk)",
            expression_attribute_names={"#pk": HASH_KEY},
        )
    )

    with pytest.raises(ConditionalCheckFailedException) as caught:
        await dynamodb.put_item(
            PutItemInput(
                table_name=table,
                item={**key, "owner": AttributeValueS("second")},
                condition_expression="attribute_not_exists(#pk)",
                expression_attribute_names={"#pk": HASH_KEY},
                return_values_on_condition_check_failure=ReturnValuesOnConditionCheckFailure.ALL_OLD,
            )
        )

    error = caught.value
    assert error.response_metadata.http_status_code == 400
    assert error.item is not None
    assert error.item["owner"] == AttributeValueS("first")
    stored = await dynamodb.get_item(
        GetItemInput(table_name=table, key=key, consistent_read=True)
    )
    assert stored.item is not None
    assert stored.item["owner"] == AttributeValueS("first")


async def test_query_paginates_in_sort_order(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies a limited query pages through one partition via last_evaluated_key, in order."""
    partition = _unique("query-")
    sort_keys = [f"item-{i:02d}" for i in range(7)]
    await _batch_put(
        dynamodb,
        table,
        [
            {HASH_KEY: AttributeValueS(partition), RANGE_KEY: AttributeValueS(sk)}
            for sk in sort_keys
        ],
    )

    seen: list[str] = []
    pages = 0
    start: Item | None = None
    while True:
        page = await dynamodb.query(
            QueryInput(
                table_name=table,
                key_condition_expression="#pk = :pk",
                expression_attribute_names={"#pk": HASH_KEY},
                expression_attribute_values={":pk": AttributeValueS(partition)},
                limit=3,
                consistent_read=True,
                exclusive_start_key=start,
            )
        )
        pages += 1
        seen.extend(_string(item[RANGE_KEY]) for item in page.items or [])
        start = page.last_evaluated_key
        if start is None:
            break

    assert seen == sort_keys
    assert pages >= 3


async def test_scan_paginates_across_all_items(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies a limited, filtered scan returns each matching item exactly once across pages."""
    partition = _unique("scan-")
    expected = {f"item-{i:02d}" for i in range(30)}
    await _batch_put(
        dynamodb,
        table,
        [
            {
                HASH_KEY: AttributeValueS(f"{partition}-{sk}"),
                RANGE_KEY: AttributeValueS(sk),
            }
            for sk in expected
        ],
    )

    seen: list[str] = []
    start: Item | None = None
    while True:
        page = await dynamodb.scan(
            ScanInput(
                table_name=table,
                filter_expression="begins_with(#pk, :prefix)",
                expression_attribute_names={"#pk": HASH_KEY},
                expression_attribute_values={":prefix": AttributeValueS(partition)},
                limit=10,
                consistent_read=True,
                exclusive_start_key=start,
            )
        )
        seen.extend(_string(item[RANGE_KEY]) for item in page.items or [])
        start = page.last_evaluated_key
        if start is None:
            break

    assert sorted(seen) == sorted(expected)


async def test_batch_write_then_batch_get_then_batch_delete(
    dynamodb: AsyncDynamoDBClient, table: str
) -> None:
    """Verifies 25 items written in one batch are read back in one batch and then deleted."""
    partition = _unique("batch-")
    keys: list[Item] = [
        {HASH_KEY: AttributeValueS(partition), RANGE_KEY: AttributeValueS(f"{i:02d}")}
        for i in range(25)
    ]
    await _batch_put(
        dynamodb,
        table,
        [{**key, "n": AttributeValueN(str(i))} for i, key in enumerate(keys)],
    )

    fetched = await _batch_get(dynamodb, table, keys)
    assert {_string(item[RANGE_KEY]): item["n"] for item in fetched} == {
        f"{i:02d}": AttributeValueN(str(i)) for i in range(25)
    }

    await _batch_write(
        dynamodb,
        table,
        [WriteRequest(delete_request=DeleteRequest(key=key)) for key in keys],
    )
    assert await _batch_get(dynamodb, table, keys) == []


async def _batch_put(
    client: AsyncDynamoDBClient, table: str, items: list[Item]
) -> None:
    await _batch_write(
        client,
        table,
        [WriteRequest(put_request=PutRequest(item=item)) for item in items],
    )


async def _batch_write(
    client: AsyncDynamoDBClient, table: str, requests: list[WriteRequest]
) -> None:
    """Write in chunks of 25, resubmitting unprocessed items a bounded number of times."""
    for start in range(0, len(requests), 25):
        pending = {table: requests[start : start + 25]}
        for _ in range(8):
            result = await client.batch_write_item(
                BatchWriteItemInput(request_items=pending)
            )
            if not result.unprocessed_items:
                break
            pending = result.unprocessed_items
        else:
            raise AssertionError("batch write left unprocessed items")


async def _batch_get(
    client: AsyncDynamoDBClient, table: str, keys: list[Item]
) -> list[Item]:
    found: list[Item] = []
    pending = {table: KeysAndAttributes(keys=keys, consistent_read=True)}
    for _ in range(8):
        result = await client.batch_get_item(BatchGetItemInput(request_items=pending))
        found.extend((result.responses or {}).get(table, []))
        if not result.unprocessed_keys:
            return found
        pending = result.unprocessed_keys
    raise AssertionError("batch get left unprocessed keys")


def _unique(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex}"


def _key(item: Item) -> Item:
    return {name: item[name] for name in (HASH_KEY, RANGE_KEY)}


def _string(value: AttributeValue) -> str:
    assert isinstance(value, AttributeValueS)
    return value.value


def _set_members(value: AttributeValue) -> frozenset[str | bytes]:
    """Set members, since DynamoDB does not preserve set order."""
    assert isinstance(value, AttributeValueSS | AttributeValueNS | AttributeValueBS)
    return frozenset(value.value)
