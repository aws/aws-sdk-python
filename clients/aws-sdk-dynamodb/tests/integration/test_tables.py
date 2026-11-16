# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Table lifecycle, from JS v3 dynamodb-features.e2e table setup."""

import pytest
from aws_sdk_dynamodb.aio.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.models import (
    AttributeValueS,
    DeleteItemInput,
    DeleteTableInput,
    DescribeTableInput,
    ListTagsOfResourceInput,
    ResourceInUseException,
    ResourceNotFoundException,
    Tag,
    TagResourceInput,
)
from waiters import wait_until

from . import (
    HASH_KEY,
    table_input,
    unique_table_name,
    wait_for_active,
    wait_for_deleted,
)


async def test_table_create_tag_describe_delete(dynamodb: AsyncDynamoDBClient) -> None:
    """Verifies a new table becomes ACTIVE, carries its tags, and is gone after deletion."""
    name = unique_table_name()
    created = await dynamodb.create_table(table_input(name))
    try:
        assert created.table_description is not None
        arn = created.table_description.table_arn
        assert arn is not None

        await wait_for_active(dynamodb, name)
        described = await dynamodb.describe_table(DescribeTableInput(table_name=name))
        assert described.table is not None
        assert described.table.table_name == name
        assert described.table.key_schema is not None
        assert described.table.key_schema[0].attribute_name == HASH_KEY

        await wait_until(
            lambda: dynamodb.tag_resource(
                TagResourceInput(resource_arn=arn, tags=[Tag(key="Extra", value="yes")])
            ),
            retry_on=(ResourceInUseException,),
            interval=2,
        )
        expected = {"Purpose": "IntegTest", "Extra": "yes"}
        listed = await wait_until(
            lambda: dynamodb.list_tags_of_resource(
                ListTagsOfResourceInput(resource_arn=arn)
            ),
            lambda output: (
                {tag.key: tag.value for tag in output.tags or []} == expected
            ),
            interval=2,
        )
        assert {tag.key: tag.value for tag in listed.tags or []} == expected
    finally:
        await wait_until(
            lambda: dynamodb.delete_table(DeleteTableInput(table_name=name)),
            retry_on=(ResourceInUseException,),
            interval=2,
        )

    await wait_for_deleted(dynamodb, name)
    with pytest.raises(ResourceNotFoundException):
        await dynamodb.delete_item(
            DeleteItemInput(table_name=name, key={HASH_KEY: AttributeValueS("x")})
        )
