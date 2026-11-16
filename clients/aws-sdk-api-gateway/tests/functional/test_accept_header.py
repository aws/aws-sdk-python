# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_api_gateway.client import APIGatewayClient
from aws_sdk_api_gateway.config import APIGatewayConfig
from aws_sdk_api_gateway.models import GetApiKeysInput, GetExportInput
from smithy_test import mock


def test_should_add_default_accept_header() -> None:
    """The client sends `Accept: application/json` when the caller sets no Accept header."""
    client = APIGatewayClient(APIGatewayConfig.resolve(region="us-west-2"))
    mock(client).expect_request(headers={"accept": "application/json"})

    client.get_api_keys(GetApiKeysInput())


def test_should_not_override_accept_header() -> None:
    """An Accept header from the caller reaches the request unchanged."""
    client = APIGatewayClient(APIGatewayConfig.resolve(region="us-west-2"))
    mock(client).expect_request(headers={"accept": "application/yaml"})

    client.get_export(
        GetExportInput(
            rest_api_id="rest-api-id",
            stage_name="stage-name",
            export_type="oas30",
            accepts="application/yaml",
        )
    )
