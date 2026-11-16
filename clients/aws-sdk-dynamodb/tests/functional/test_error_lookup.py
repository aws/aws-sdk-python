# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import DescribeTableInput, ResourceNotFoundException
from pytest import raises
from smithy_test import mock


def test_looks_up_errors_by_shape_name_rather_than_the_apparent_shape_id() -> None:
    """An error resolves to its modeled exception by shape name, ignoring the namespace in `__type`."""
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        status_code=400,
        headers={"content-type": "application/x-amz-json-1.0"},
        body='{"__type": "com.amazon.coral.service#ResourceNotFoundException",'
        ' "message": "Requested resource not found"}',
    )

    with raises(ResourceNotFoundException, match="Requested resource not found"):
        client.describe_table(DescribeTableInput(table_name="my-table"))
