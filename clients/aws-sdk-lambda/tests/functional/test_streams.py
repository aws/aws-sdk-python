# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from io import BytesIO

import pytest
from aws_sdk_lambda.client import LambdaClient
from aws_sdk_lambda.config import LambdaConfig
from aws_sdk_lambda.models import InvokeInput
from smithy_test import mock

PAYLOAD = json.dumps({"hello": "world"}, separators=(",", ":"))


# TODO: accept str for blob members
@pytest.mark.skip
def test_should_be_uniform_between_str_and_bytes_payloads() -> None:
    """A str payload and its bytes encoding produce the same request."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="POST",
        hostname="lambda.us-west-2.amazonaws.com",
        headers={"content-type": "application/octet-stream", "content-length": "17"},
        body='{"hello":"world"}',
        scheme="https",
        path="/2015-03-31/functions/echo/invocations",
    ).times(2)

    client.invoke(InvokeInput(function_name="echo", payload=PAYLOAD))  # pyright: ignore[reportArgumentType]
    client.invoke(InvokeInput(function_name="echo", payload=PAYLOAD.encode()))


# TODO: accept str for blob members
@pytest.mark.skip
def test_should_allow_str_as_payload_blob_and_decode_output_payload() -> None:
    """The client accepts a str payload, and the output payload converts to a str."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="POST",
        hostname="lambda.us-west-2.amazonaws.com",
        headers={"content-type": "application/octet-stream"},
        body=PAYLOAD,
        scheme="https",
        path="/2015-03-31/functions/echo/invocations",
    ).respond_with(body=PAYLOAD)

    output = client.invoke(InvokeInput(function_name="echo", payload=PAYLOAD))  # pyright: ignore[reportArgumentType]

    assert json.loads((output.payload or b"{}").decode()) == {"hello": "world"}


def test_should_allow_bytes_as_payload_blob() -> None:
    """A bytes payload becomes the request body."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="POST",
        hostname="lambda.us-west-2.amazonaws.com",
        headers={"content-type": "application/octet-stream"},
        body=PAYLOAD,
        scheme="https",
        path="/2015-03-31/functions/echo/invocations",
    ).respond_with(body=PAYLOAD)

    output = client.invoke(InvokeInput(function_name="echo", payload=PAYLOAD.encode()))

    assert json.loads((output.payload or b"{}").decode()) == {"hello": "world"}


def test_should_allow_bytearray_as_payload_blob() -> None:
    """A bytearray payload becomes the request body."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="POST",
        hostname="lambda.us-west-2.amazonaws.com",
        headers={"content-type": "application/octet-stream"},
        body=PAYLOAD,
        scheme="https",
        path="/2015-03-31/functions/echo/invocations",
    ).respond_with(body=PAYLOAD)

    output = client.invoke(
        InvokeInput(function_name="echo", payload=bytearray(PAYLOAD.encode()))  # pyright: ignore[reportArgumentType]
    )

    assert json.loads((output.payload or b"{}").decode()) == {"hello": "world"}


def test_should_allow_file_like_object_as_payload_blob() -> None:
    """A file-like payload becomes the request body."""
    client = LambdaClient(LambdaConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="POST",
        hostname="lambda.us-west-2.amazonaws.com",
        headers={"content-type": "application/octet-stream"},
        body=PAYLOAD,
        scheme="https",
        path="/2015-03-31/functions/echo/invocations",
    ).respond_with(body=PAYLOAD)

    output = client.invoke(
        InvokeInput(function_name="echo", payload=BytesIO(PAYLOAD.encode()))  # pyright: ignore[reportArgumentType]
    )

    assert json.loads((output.payload or b"{}").decode()) == {"hello": "world"}
