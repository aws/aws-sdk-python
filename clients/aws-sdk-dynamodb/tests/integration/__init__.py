# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live DynamoDB integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_dynamodb.aio.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.aio.config import AsyncDynamoDBConfig
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import (
    AttributeDefinition,
    BillingMode,
    CreateTableInput,
    DescribeTableInput,
    DescribeTableOutput,
    KeySchemaElement,
    KeyType,
    ResourceNotFoundException,
    ScalarAttributeType,
    TableStatus,
    Tag,
)
from waiters import wait_until, wait_until_gone

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
TABLE_PREFIX = "aws-sdk-python-integ-"

HASH_KEY = "pk"
RANGE_KEY = "sk"

TABLE_WAIT_SECONDS = 600.0


def unique_table_name() -> str:
    return f"{TABLE_PREFIX}{uuid.uuid4().hex[:16]}"


def table_input(name: str) -> CreateTableInput:
    """A pay-per-request table with a string hash and range key."""
    return CreateTableInput(
        table_name=name,
        attribute_definitions=[
            AttributeDefinition(
                attribute_name=HASH_KEY, attribute_type=ScalarAttributeType.S
            ),
            AttributeDefinition(
                attribute_name=RANGE_KEY, attribute_type=ScalarAttributeType.S
            ),
        ],
        key_schema=[
            KeySchemaElement(attribute_name=HASH_KEY, key_type=KeyType.HASH),
            KeySchemaElement(attribute_name=RANGE_KEY, key_type=KeyType.RANGE),
        ],
        billing_mode=BillingMode.PAY_PER_REQUEST,
        tags=[Tag(key="Purpose", value="IntegTest")],
    )


async def create_async_client() -> AsyncDynamoDBClient:
    config = await AsyncDynamoDBConfig.resolve(region=REGION)
    return AsyncDynamoDBClient(config=config)


def create_sync_client() -> DynamoDBClient:
    config = DynamoDBConfig.resolve(region=REGION)
    return DynamoDBClient(config=config)


async def wait_for_active(client: AsyncDynamoDBClient, name: str) -> None:
    """Waits until the table is visible and ACTIVE."""

    async def describe() -> DescribeTableOutput:
        return await client.describe_table(DescribeTableInput(table_name=name))

    await wait_until(
        describe,
        lambda described: (
            described.table is not None
            and described.table.table_status == TableStatus.ACTIVE
        ),
        # CreateTable is eventually consistent, so the table may not be visible yet.
        retry_on=(ResourceNotFoundException,),
        interval=2,
        timeout=TABLE_WAIT_SECONDS,
    )


async def wait_for_deleted(client: AsyncDynamoDBClient, name: str) -> None:
    """Waits until DescribeTable reports the table gone."""
    await wait_until_gone(
        lambda: client.describe_table(DescribeTableInput(table_name=name)),
        gone_on=(ResourceNotFoundException,),
        interval=2,
        timeout=TABLE_WAIT_SECONDS,
    )
