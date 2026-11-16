# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json

import pytest
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import ScanInput
from smithy_test import mock


# TODO: generate paginators
@pytest.mark.skip
def test_makes_sequential_requests_using_a_pagination_token() -> None:
    # Imported here so the missing paginator fails this test, not collection.
    """The paginator sends the LastEvaluatedKey of each page as the ExclusiveStartKey of the next request."""
    from aws_sdk_dynamodb.paginators import (  # pyright: ignore[reportMissingImports]
        paginate_scan,  # pyright: ignore[reportUnknownVariableType]
    )

    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller = mock(client)

    def is_first_page(body: bytes) -> None:
        assert b"TableName" in body
        assert b"ExclusiveStartKey" not in body

    controller.expect_request(hostname="/dynamodb/", body=is_first_page).respond_with(
        status_code=200,
        headers={},
        body=json.dumps(
            {
                "Items": [
                    {"id": {"S": "1"}, "name": {"S": "Item 1"}},
                    {"id": {"S": "2"}, "name": {"S": "Item 2"}},
                ],
                "Count": 2,
                "ScannedCount": 2,
                "LastEvaluatedKey": {"id": {"S": "2"}},
            }
        ),
    )
    controller.expect_request(
        hostname="/dynamodb/", body="/ExclusiveStartKey/"
    ).respond_with(
        status_code=200,
        headers={},
        body=json.dumps(
            {
                "Items": [
                    {"id": {"S": "3"}, "name": {"S": "Item 3"}},
                    {"id": {"S": "4"}, "name": {"S": "Item 4"}},
                ],
                "Count": 2,
                "ScannedCount": 2,
            }
        ),
    )
    request_params = ScanInput(table_name="test")

    pages = 0
    for _ in paginate_scan(client, request_params):  # pyright: ignore[reportUnknownVariableType]
        pages += 1

    assert pages == 2
    assert len(controller.requests) == 2
