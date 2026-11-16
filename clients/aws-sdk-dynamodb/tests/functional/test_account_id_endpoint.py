# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_dynamodb.client import DynamoDBClient
from aws_sdk_dynamodb.config import DynamoDBConfig
from aws_sdk_dynamodb.models import ListTablesInput
from smithy_aws_core.identity.components import AWSCredentialsIdentity
from smithy_aws_core.identity.static import StaticCredentialsResolver
from smithy_core.exceptions import EndpointResolutionError
from smithy_test import mock

REGION = "us-west-2"


# TODO: let the HTTP mock keep the account ID of the credentials it replaces
@pytest.mark.skip
def test_should_default_to_resolving_endpoint_with_account_id_when_it_is_available_in_the_client_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the credentials carry an account ID, the endpoint hostname starts with that account ID."""
    monkeypatch.delenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", raising=False)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_credentials_identity_resolver=StaticCredentialsResolver(
                identity=AWSCredentialsIdentity(
                    access_key_id="INTEG_TEST",
                    secret_access_key="INTEG_TEST",
                    account_id="123456789012",
                )
            ),
        )
    )
    controller = mock(client)
    controller.expect_request(hostname="/123456789012.ddb.us-west-2.amazonaws.com/")

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


# TODO: let the HTTP mock keep the account ID of the credentials it replaces
@pytest.mark.skip
@pytest.mark.parametrize(
    ("expected_hostname_prefix", "mode"),
    [
        ("dynamodb", "disabled"),
        ("123456789012.ddb", "preferred"),
        ("123456789012.ddb", "required"),
    ],
)
def test_should_match_prefix_for_when_account_id_endpoint_mode_is_set_in_config(
    monkeypatch: pytest.MonkeyPatch, expected_hostname_prefix: str, mode: str
) -> None:
    """The account_id_endpoint_mode config value decides whether the hostname carries the account ID prefix."""
    monkeypatch.delenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", raising=False)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_credentials_identity_resolver=StaticCredentialsResolver(
                identity=AWSCredentialsIdentity(
                    access_key_id="INTEG_TEST",
                    secret_access_key="INTEG_TEST",
                    account_id="123456789012",
                )
            ),
            account_id_endpoint_mode=mode,
        )
    )
    controller = mock(client)
    controller.expect_request(
        hostname=f"{expected_hostname_prefix}.{REGION}.amazonaws.com"
    )

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


# TODO: let the HTTP mock keep the account ID of the credentials it replaces
@pytest.mark.skip
@pytest.mark.parametrize(
    ("expected_hostname_prefix", "mode"),
    [
        ("dynamodb", "disabled"),
        ("123456789012.ddb", "preferred"),
        ("123456789012.ddb", "required"),
    ],
)
def test_should_match_prefix_for_when_account_id_endpoint_mode_is_set_in_env(
    monkeypatch: pytest.MonkeyPatch, expected_hostname_prefix: str, mode: str
) -> None:
    """The AWS_ACCOUNT_ID_ENDPOINT_MODE environment variable decides whether the hostname carries the account ID prefix."""
    monkeypatch.setenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", mode)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_credentials_identity_resolver=StaticCredentialsResolver(
                identity=AWSCredentialsIdentity(
                    access_key_id="INTEG_TEST",
                    secret_access_key="INTEG_TEST",
                    account_id="123456789012",
                )
            ),
        )
    )
    controller = mock(client)
    controller.expect_request(
        hostname=f"{expected_hostname_prefix}.{REGION}.amazonaws.com"
    )

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


def test_should_omit_account_id_prefix_when_credentials_lack_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the credentials lack an account ID, the hostname lacks the account ID prefix."""
    monkeypatch.delenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", raising=False)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_access_key_id="INTEG_TEST",
            aws_secret_access_key="INTEG_TEST",
        )
    )
    controller = mock(client)
    controller.expect_request(hostname="/dynamodb.us-west-2.amazonaws.com/")

    client.list_tables(ListTablesInput())

    assert len(controller.requests) == 1


def test_will_fail_if_required_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint resolution fails when the environment requires an account ID and the credentials lack one."""
    monkeypatch.setenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", "required")
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_access_key_id="INTEG_TEST",
            aws_secret_access_key="INTEG_TEST",
        )
    )
    controller = mock(client)
    controller.expect_request()

    with pytest.raises(EndpointResolutionError):
        client.list_tables(ListTablesInput())


def test_will_fail_if_required_by_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint resolution fails when the config requires an account ID and the credentials lack one."""
    monkeypatch.delenv("AWS_ACCOUNT_ID_ENDPOINT_MODE", raising=False)
    client = DynamoDBClient(
        DynamoDBConfig.resolve(
            region=REGION,
            aws_access_key_id="INTEG_TEST",
            aws_secret_access_key="INTEG_TEST",
            account_id_endpoint_mode="required",
        )
    )
    controller = mock(client)
    controller.expect_request()

    with pytest.raises(EndpointResolutionError):
        client.list_tables(ListTablesInput())
