# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live SQS integration tests, written once and run in both sync and async modes."""

import struct
import uuid

from aws_sdk_sqs.aio.client import AsyncSQSClient
from aws_sdk_sqs.aio.config import AsyncSQSConfig
from aws_sdk_sqs.client import SQSClient
from aws_sdk_sqs.config import SQSConfig
from aws_sdk_sqs.models import Message, MessageAttributeValue, ReceiveMessageInput
from waiters import wait_until

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
QUEUE_PREFIX = "aws-sdk-python-integ-"


def unique_queue_name(infix: str = "") -> str:
    return f"{QUEUE_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncSQSClient:
    config = await AsyncSQSConfig.resolve(region=REGION)
    return AsyncSQSClient(config=config)


def create_sync_client() -> SQSClient:
    config = SQSConfig.resolve(region=REGION)
    return SQSClient(config=config)


async def receive_messages(
    sqs: AsyncSQSClient,
    queue_url: str,
    count: int,
    *,
    message_attribute_names: list[str] | None = None,
    timeout: float = 60.0,
) -> list[Message]:
    """Long-polls until ``count`` messages arrive."""
    received: list[Message] = []

    async def receive() -> list[Message]:
        output = await sqs.receive_message(
            ReceiveMessageInput(
                queue_url=queue_url,
                max_number_of_messages=10,
                wait_time_seconds=10,
                message_attribute_names=message_attribute_names,
            )
        )
        received.extend(output.messages or [])
        return received

    # The long poll already paces each read.
    return await wait_until(
        receive, lambda messages: len(messages) >= count, interval=0, timeout=timeout
    )


def md5_of_message_attributes_input(
    attributes: dict[str, MessageAttributeValue],
) -> bytes:
    """Serialize attributes in the byte layout SQS hashes for MD5OfMessageAttributes."""
    parts: list[bytes] = []
    for name in sorted(attributes):
        attribute = attributes[name]
        for text in (name, attribute.data_type):
            encoded = text.encode()
            parts.append(struct.pack(">I", len(encoded)) + encoded)
        if attribute.binary_value is not None:
            value = attribute.binary_value
            parts.append(b"\x02")
        else:
            value = (attribute.string_value or "").encode()
            parts.append(b"\x01")
        parts.append(struct.pack(">I", len(value)) + value)
    return b"".join(parts)
