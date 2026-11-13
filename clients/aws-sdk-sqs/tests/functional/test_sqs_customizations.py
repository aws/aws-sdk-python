# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from hashlib import md5

import pytest
from aws_sdk_sqs.client import SQSClient
from aws_sdk_sqs.config import SQSConfig
from aws_sdk_sqs.models import (
    ReceiveMessageInput,
    SendMessageBatchInput,
    SendMessageBatchRequestEntry,
    SendMessageInput,
)
from pytest import raises
from smithy_test import mock

JSON_HEADERS = {"content-type": "application/x-amz-json-1.0"}
CORRECT_MD5 = md5(b"body").hexdigest()
INCORRECT_MD5 = md5(b"bodya").hexdigest()


def test_runs_md5_checksums_on_received_messages_with_correct_md5_hashes() -> None:
    """ReceiveMessage accepts messages whose MD5 digests match their bodies."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps(
            {
                "Messages": [
                    {"MessageId": "MSGID", "MD5OfBody": CORRECT_MD5, "Body": "body"}
                ]
            }
        ),
    )

    receive = client.receive_message(
        ReceiveMessageInput(queue_url="https://my-queue.queue")
    )

    assert receive.messages is not None
    assert receive.messages[0].body == "body"


def test_runs_md5_checksums_on_sent_messages_with_correct_md5_hashes() -> None:
    """SendMessage accepts a response whose MD5 digest matches the sent body."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps({"MD5OfMessageBody": CORRECT_MD5, "MessageId": "MSGID"}),
    )

    send = client.send_message(
        SendMessageInput(queue_url="https://my-queue.queue", message_body="body")
    )

    assert send.message_id == "MSGID"


def test_runs_md5_checksums_on_batch_sent_messages_with_correct_md5_hashes() -> None:
    """SendMessageBatch accepts responses whose MD5 digests match the sent bodies."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps(
            {
                "Successful": [
                    {"Id": id, "MessageId": id, "MD5OfMessageBody": CORRECT_MD5}
                    for id in ("MSGID1", "MSGID2", "MSGID3")
                ]
            }
        ),
    )

    batch_send = client.send_message_batch(
        SendMessageBatchInput(
            queue_url="https://my-queue.queue",
            entries=[
                SendMessageBatchRequestEntry(id="MSGID1", message_body="body"),
                SendMessageBatchRequestEntry(id="MSGID2", message_body="body"),
                SendMessageBatchRequestEntry(id="MSGID3", message_body="body"),
            ],
        )
    )

    assert batch_send.successful[0].message_id == "MSGID1"


# TODO: validate SQS message MD5 digests
@pytest.mark.skip
def test_runs_md5_checksums_on_received_messages_with_incorrect_md5_hashes() -> None:
    """ReceiveMessage raises an error for a message whose MD5 digest mismatches its body."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps(
            {
                "Messages": [
                    {"MessageId": "MSGID", "MD5OfBody": INCORRECT_MD5, "Body": "body"}
                ]
            }
        ),
    )

    with raises(Exception, match="Invalid MD5 checksum"):
        client.receive_message(ReceiveMessageInput(queue_url="https://my-queue.queue"))


# TODO: validate SQS message MD5 digests
@pytest.mark.skip
def test_runs_md5_checksums_on_sent_messages_with_incorrect_md5_hashes() -> None:
    """SendMessage raises an error for a response whose MD5 digest mismatches the sent body."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps({"MD5OfMessageBody": INCORRECT_MD5, "MessageId": "MSGID"}),
    )

    with raises(Exception, match="InvalidChecksumError"):
        client.send_message(
            SendMessageInput(queue_url="https://my-queue.queue", message_body="body")
        )


# TODO: validate SQS message MD5 digests
@pytest.mark.skip
def test_runs_md5_checksums_on_batch_sent_messages_with_incorrect_md5_hashes() -> None:
    """SendMessageBatch raises an error for a response whose MD5 digest mismatches a sent body."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request().respond_with(
        headers=JSON_HEADERS,
        body=json.dumps(
            {
                "Successful": [
                    {"Id": id, "MessageId": id, "MD5OfMessageBody": INCORRECT_MD5}
                    for id in ("MSGID1", "MSGID2", "MSGID3")
                ]
            }
        ),
    )

    with raises(Exception, match="Invalid MD5 checksum"):
        client.send_message_batch(
            SendMessageBatchInput(
                queue_url="https://my-queue.queue",
                entries=[
                    SendMessageBatchRequestEntry(id="MSGID1", message_body="body"),
                    SendMessageBatchRequestEntry(id="MSGID2", message_body="body"),
                    SendMessageBatchRequestEntry(id="MSGID3", message_body="body"),
                ],
            )
        )


# TODO: use QueueUrl as the endpoint
@pytest.mark.skip
def test_should_send_the_x_amzn_query_mode_header_when_in_aws_query_compatible_mode() -> (
    None
):
    """Requests carry `x-amzn-query-mode: true` for the awsQuery-compatible protocol."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        hostname="abc.com",
        scheme="https",
        path="/",
        headers={"x-amzn-query-mode": "true"},
    )

    client.send_message(
        SendMessageInput(queue_url="https://abc.com/123/MyQueue", message_body="hello")
    )


# TODO: use QueueUrl as the endpoint
@pytest.mark.skip
def test_should_override_resolved_endpoint_by_default() -> None:
    """The QueueUrl input replaces the resolved endpoint."""
    client = SQSClient(SQSConfig.resolve(region="us-west-2"))
    mock(client).expect_request(hostname="abc.com", scheme="https", path="/")

    client.send_message(
        SendMessageInput(queue_url="https://abc.com/123/MyQueue", message_body="hello")
    )


# TODO: add the use_queue_url_as_endpoint config option
@pytest.mark.skip
def test_does_not_override_endpoint_if_shut_off_with_use_queue_url_as_endpoint_false() -> (
    None
):
    """With use_queue_url_as_endpoint set to False, the resolved endpoint stays in place."""
    client = SQSClient(
        SQSConfig.resolve(  # pyright: ignore[reportUnknownArgumentType]
            region="us-west-2",
            use_queue_url_as_endpoint=False,  # pyright: ignore[reportCallIssue]
        )
    )
    mock(client).expect_request(
        hostname="sqs.us-west-2.amazonaws.com", scheme="https", path="/"
    )

    client.send_message(
        SendMessageInput(queue_url="https://abc.com/123/MyQueue", message_body="hello")
    )


def test_does_not_override_endpoint_if_custom_endpoint_given_to_client() -> None:
    """A custom client endpoint takes precedence over the QueueUrl input."""
    client = SQSClient(
        SQSConfig.resolve(
            region="us-west-2", endpoint_uri="https://custom-endpoint.com/"
        )
    )
    mock(client).expect_request(
        hostname="custom-endpoint.com", scheme="https", path="/"
    )

    client.send_message(
        SendMessageInput(queue_url="https://abc.com/123/MyQueue", message_body="hello")
    )
