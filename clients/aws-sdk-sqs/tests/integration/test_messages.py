# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Message round trips, from JS v3 sqs-messages-features.e2e."""

import hashlib

from aws_sdk_sqs.aio.client import AsyncSQSClient
from aws_sdk_sqs.models import (
    ChangeMessageVisibilityInput,
    DeleteMessageBatchInput,
    DeleteMessageBatchRequestEntry,
    DeleteMessageInput,
    MessageAttributeValue,
    ReceiveMessageInput,
    SendMessageBatchInput,
    SendMessageBatchRequestEntry,
    SendMessageInput,
)

from waiters import wait_until

from . import md5_of_message_attributes_input, receive_messages
from .conftest import QueueFactory


async def test_send_message_md5_matches_body_and_receive_returns_it(
    sqs: AsyncSQSClient, queue_url: str
) -> None:
    """Sent and received bodies carry the MD5 of the original body."""
    body = "HELLO"
    expected_md5 = hashlib.md5(body.encode()).hexdigest()

    sent = await sqs.send_message(
        SendMessageInput(queue_url=queue_url, message_body=body)
    )
    assert sent.message_id
    assert sent.md5_of_message_body == expected_md5

    [message] = await receive_messages(sqs, queue_url, 1)
    assert message.body == body
    assert message.md5_of_body == expected_md5
    assert message.message_id == sent.message_id


async def test_string_number_and_binary_attributes_round_trip(
    sqs: AsyncSQSClient, queue_url: str
) -> None:
    """Attributes of every scalar type survive a round trip and hash to the MD5 SQS reports."""
    attributes = {
        "text": MessageAttributeValue(data_type="String", string_value="héllo"),
        "count": MessageAttributeValue(data_type="Number", string_value="42"),
        "binary": MessageAttributeValue(
            data_type="Binary", binary_value=bytes([1, 2, 3, 255])
        ),
    }

    sent = await sqs.send_message(
        SendMessageInput(
            queue_url=queue_url, message_body="HELLO", message_attributes=attributes
        )
    )
    expected_md5 = hashlib.md5(md5_of_message_attributes_input(attributes)).hexdigest()
    assert sent.md5_of_message_attributes == expected_md5

    [message] = await receive_messages(
        sqs, queue_url, 1, message_attribute_names=["All"]
    )
    received = message.message_attributes or {}
    assert set(received) == set(attributes)
    assert received["text"].string_value == "héllo"
    assert received["count"].data_type == "Number"
    assert received["count"].string_value == "42"
    assert received["binary"].binary_value == bytes([1, 2, 3, 255])
    assert message.md5_of_message_attributes == expected_md5


async def test_send_message_batch_delivers_every_entry_and_batch_delete_empties_queue(
    sqs: AsyncSQSClient, queue_url: str
) -> None:
    """A batch send is received in full and a batch delete removes every message."""
    bodies = {f"entry-{i}": f"body {i}" for i in range(5)}
    sent = await sqs.send_message_batch(
        SendMessageBatchInput(
            queue_url=queue_url,
            entries=[
                SendMessageBatchRequestEntry(
                    id=entry_id,
                    message_body=body,
                    message_attributes={
                        "index": MessageAttributeValue(
                            data_type="Number", string_value=entry_id[-1]
                        )
                    },
                )
                for entry_id, body in bodies.items()
            ],
        )
    )
    assert not sent.failed
    assert {entry.id for entry in sent.successful or []} == set(bodies)
    for entry in sent.successful or []:
        assert (
            entry.md5_of_message_body
            == hashlib.md5(bodies[entry.id].encode()).hexdigest()
        )

    messages = await receive_messages(sqs, queue_url, len(bodies))
    assert sorted(message.body or "" for message in messages) == sorted(bodies.values())

    deleted = await sqs.delete_message_batch(
        DeleteMessageBatchInput(
            queue_url=queue_url,
            entries=[
                DeleteMessageBatchRequestEntry(
                    id=str(i), receipt_handle=message.receipt_handle or ""
                )
                for i, message in enumerate(messages)
            ],
        )
    )
    assert not deleted.failed
    assert len(deleted.successful or []) == len(bodies)


async def test_change_message_visibility_to_zero_makes_message_receivable_again(
    sqs: AsyncSQSClient, queue_url: str
) -> None:
    """Zeroing the visibility timeout of an in-flight message releases it immediately."""
    await sqs.send_message(SendMessageInput(queue_url=queue_url, message_body="again"))
    [first] = await receive_messages(sqs, queue_url, 1)
    # The default 30s visibility timeout means a second receive can only succeed after the change.
    assert first.receipt_handle is not None

    await sqs.change_message_visibility(
        ChangeMessageVisibilityInput(
            queue_url=queue_url,
            receipt_handle=first.receipt_handle,
            visibility_timeout=0,
        )
    )

    [second] = await receive_messages(sqs, queue_url, 1, timeout=20)
    assert second.message_id == first.message_id
    assert second.receipt_handle != first.receipt_handle


async def test_deleted_message_is_not_redelivered_after_visibility_timeout(
    sqs: AsyncSQSClient, make_queue: QueueFactory
) -> None:
    """A deleted message stays gone while an undeleted one reappears after the visibility timeout."""
    queue_url = await make_queue(attributes={"VisibilityTimeout": "2"})
    await sqs.send_message_batch(
        SendMessageBatchInput(
            queue_url=queue_url,
            entries=[
                SendMessageBatchRequestEntry(id="keep", message_body="keep"),
                SendMessageBatchRequestEntry(id="drop", message_body="drop"),
            ],
        )
    )

    messages = await receive_messages(sqs, queue_url, 2)
    assert {message.body for message in messages} == {"keep", "drop"}
    dropped = next(message for message in messages if message.body == "drop")
    await sqs.delete_message(
        DeleteMessageInput(queue_url=queue_url, receipt_handle=dropped.receipt_handle)
    )

    redelivered: set[str] = set()

    async def receive() -> set[str]:
        output = await sqs.receive_message(
            ReceiveMessageInput(
                queue_url=queue_url, max_number_of_messages=10, wait_time_seconds=5
            )
        )
        redelivered.update(message.body or "" for message in output.messages or [])
        return redelivered

    # The long poll already paces each read.
    await wait_until(receive, lambda seen: "keep" in seen, interval=0, timeout=30)
    assert "keep" in redelivered
    assert "drop" not in redelivered
