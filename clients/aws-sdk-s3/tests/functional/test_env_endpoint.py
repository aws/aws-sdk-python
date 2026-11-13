# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import ListBucketsInput
from smithy_test import mock


def test_should_override_a_client_endpoint_if_none_is_set_on_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AWS_ENDPOINT_URL sets the endpoint of a client configured without one."""
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://localhost/1")
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(hostname="/localhost/", path="/\\/1/")

        client.list_buckets(ListBucketsInput())


def test_should_defer_to_the_client_s_manually_set_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An endpoint set on the client takes precedence over AWS_ENDPOINT_URL."""
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://localhost/1")
    client = S3Client(
        S3Config.resolve(region="us-west-2", endpoint_uri="https://localhost/2")
    )
    with mock(client) as controller:
        controller.expect_request(hostname="/localhost/", path="/\\/2/")

        client.list_buckets(ListBucketsInput())


def test_should_allow_a_specific_service_id_to_be_chosen_in_the_env_variable_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AWS_ENDPOINT_URL_S3 sets the endpoint for the S3 client."""
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "https://localhost/1")
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(hostname="/s3\\.us-west-2\\.amazonaws\\.com/")

        client.list_buckets(ListBucketsInput())
