# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import ListTablesInput
from smithy_test import mock


def test_should_override_a_client_endpoint_if_none_is_set_on_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AWS_ENDPOINT_URL sets the endpoint of a client configured without one."""
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://localhost/1")
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname="/localhost/", path="/\\/1/")

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


def test_should_defer_to_the_clients_manually_set_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An endpoint set on the client takes precedence over AWS_ENDPOINT_URL."""
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://localhost/1")
    client = DynamoDBClient(
        DynamoDBConfig.resolve(region="us-west-2", endpoint_uri="https://localhost/2")
    )
    controller = mock(client)
    controller.expect_request(hostname="/localhost/", path="/\\/2/")

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


def test_should_allow_a_specific_service_id_to_be_chosen_in_the_env_variable_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AWS_ENDPOINT_URL_DYNAMODB sets the endpoint for the DynamoDB client."""
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://localhost/1")
    client = DynamoDBClient(DynamoDBConfig.resolve(region="us-west-2"))
    controller = mock(client)
    controller.expect_request(hostname="/localhost/", path="/\\/1/")

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1
