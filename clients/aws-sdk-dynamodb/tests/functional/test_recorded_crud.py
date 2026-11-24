# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Table and item CRUD, replayed from a recording of the live service.

Record against AWS with ``SMITHY_PYTHON_TEST_MODE=record pytest <this file>``.

The recording is in ``recordings/<test function>/<client>.py``. It serves both clients,
because playback answers by operation and never looks at the request.
"""

from collections.abc import Mapping
import os
from contextlib import AsyncExitStack
from typing import cast
from uuid import uuid4

import pytest
from aws_sdk_dynamodb.aio.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.aio.config import AsyncDynamoDBConfig
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import AttributeValue, AttributeValueDict, AttributeValueN
from dual_mode import MODES, AwaitableClient, Mode
from smithy_test import instrument
from smithy_test.aio import instrument_async
from waiters import wait_until

REGION = "us-west-2"
RECORDING = os.environ.get("SMITHY_PYTHON_TEST_MODE") == "record"


@pytest.mark.parametrize("mode", MODES)
async def test_table_and_item_crud(mode: Mode) -> None:
    table = f"aws-sdk-python-recorded-{uuid4().hex[:8]}"

    async with AsyncExitStack() as stack:
        if mode == "async":
            client = AsyncDynamoDBClient(
                await AsyncDynamoDBConfig.resolve(region=REGION)
            )
            await stack.enter_async_context(client)
            await stack.enter_async_context(await instrument_async(client))
            ddb = client
        else:
            sync = DynamoDBClient(DynamoDBConfig.resolve(region=REGION))
            stack.enter_context(instrument(sync))
            adapter = await stack.enter_async_context(AwaitableClient(sync))
            ddb = cast(AsyncDynamoDBClient, adapter)

        await ddb.create_table(
            table_name=table,
            attribute_definitions=[{"attribute_name": "id", "attribute_type": "S"}],
            key_schema=[{"attribute_name": "id", "key_type": "HASH"}],
            billing_mode="PAY_PER_REQUEST",
        )
        try:
            await wait_until(
                lambda: ddb.describe_table(table_name=table),
                lambda described: (
                    described.table is not None
                    and described.table.table_status == "ACTIVE"
                ),
                # Playback answers at once, so there is nothing to wait for.
                interval=0.5 if RECORDING else 0,
            )

            item: Mapping[str, AttributeValue | AttributeValueDict] = {
                "id": {"s": "a"},
                "count": {"n": "1"},
                "profile": {"m": {"name": {"s": "Ann"}, "admin": {"bool_": True}}},
                "tags": {"ss": ["x", "y"]},
            }
            await ddb.put_item(table_name=table, item=item)
            got = await ddb.get_item(
                table_name=table, key={"id": {"s": "a"}}, consistent_read=True
            )
            assert got.item is not None
            assert got.item["count"] == AttributeValueN("1")

            await ddb.update_item(
                table_name=table,
                key={"id": {"s": "a"}},
                update_expression="SET #c = #c + :one",
                expression_attribute_names={"#c": "count"},
                expression_attribute_values={":one": {"n": "1"}},
            )
            updated = await ddb.get_item(
                table_name=table, key={"id": {"s": "a"}}, consistent_read=True
            )
            assert updated.item is not None
            assert updated.item["count"] == AttributeValueN("2")

            scanned = await ddb.scan(table_name=table, consistent_read=True)
            assert scanned.count == 1

            await ddb.delete_item(table_name=table, key={"id": {"s": "a"}})
            gone = await ddb.get_item(
                table_name=table, key={"id": {"s": "a"}}, consistent_read=True
            )
            assert not gone.item
        finally:
            await ddb.delete_table(table_name=table)
