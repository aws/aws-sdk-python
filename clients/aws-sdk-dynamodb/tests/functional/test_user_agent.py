# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re

import pytest
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import AttributeValueS, GetItemInput
from smithy_aws_core.identity.components import AWSCredentialsIdentity
from smithy_aws_core.identity.static import StaticCredentialsResolver
from smithy_test import mock


# TODO: add the O and R user agent feature IDs, and let the HTTP mock keep the account ID of the credentials it replaces
@pytest.mark.skip
def test_should_detect_account_id_and_account_id_mode() -> None:
    """The user agent lists the feature IDs for the resolved account ID and the account ID endpoint mode."""
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region="us-west-2",
            account_id_endpoint_mode="required",
            aws_credentials_identity_resolver=StaticCredentialsResolver(
                identity=AWSCredentialsIdentity(
                    access_key_id="", secret_access_key="", account_id="123456789012"
                )
            ),
        )
    )
    controller = mock(client)

    def has_features(user_agent: str) -> None:
        match = re.search(r"(?:^| )m/(\S*)", user_agent)
        assert match is not None
        features = match.group(1).split(",")
        assert "E" in features  # RETRY_MODE_STANDARD
        assert "O" in features  # ACCOUNT_ID_ENDPOINT
        assert "R" in features  # ACCOUNT_ID_MODE_REQUIRED

    controller.expect_request(headers={"user-agent": has_features})

    client.get_item(GetItemInput(table_name="table", key={"id": AttributeValueS("1")}))

    assert len(controller.requests) == 1
