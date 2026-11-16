# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json

from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import AttributeValueS, ScanInput
from smithy_test import mock


def test_should_allow_reusing_an_input_object() -> None:
    """One input object sent in two calls produces two identical requests and stays unmodified."""
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            hostname="/dynamodb/",
            body=lambda body: (
                json.loads(body)
                == {
                    "ExpressionAttributeValues": {":id": {"S": "1"}},
                    "FilterExpression": "id = :id",
                    "TableName": "test",
                }
            ),
        )
        for start_key in ["abc", "def", "ghi"]:
            controller.expect_request(
                hostname="/dynamodb/",
                body=lambda body, start_key=start_key: (
                    json.loads(body)
                    == {
                        "ExpressionAttributeValues": {":id": {"S": "1"}},
                        "FilterExpression": "id = :id",
                        "TableName": "test",
                        "ExclusiveStartKey": {"id": {"S": start_key}},
                    }
                ),
            )
        params = ScanInput(
            table_name="test",
            filter_expression="id = :id",
            expression_attribute_values={":id": AttributeValueS("1")},
        )

        client.scan(params)
        params.exclusive_start_key = {"id": AttributeValueS("abc")}
        client.scan(params)
        params.exclusive_start_key = {"id": AttributeValueS("def")}
        client.scan(params)
        params.exclusive_start_key = {"id": AttributeValueS("ghi")}
        client.scan(params)

    assert len(controller.requests) == 4
    assert params == ScanInput(
        table_name="test",
        filter_expression="id = :id",
        expression_attribute_values={":id": AttributeValueS("1")},
        exclusive_start_key={"id": AttributeValueS("ghi")},
    )
