# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional event stream handling for the Chat API."""

import asyncio
import uuid

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_qbusiness.models import (
    ChatInputStream,
    ChatInputStreamConfigurationEvent,
    ChatInputStreamEndOfInputEvent,
    ChatInputStreamTextEvent,
    ChatOutput,
    ChatOutputStream,
    ChatOutputStreamMetadataEvent,
    ChatOutputStreamTextEvent,
    ChatOutputStreamUnknown,
    ConfigurationEvent,
    EndOfInputEvent,
    TextInputEvent,
)

from . import REGION, create_qbusiness_client


async def _send_chat_events(
    stream: DuplexEventStream[ChatInputStream, ChatOutputStream, ChatOutput],
) -> None:
    """Send chat input events: configuration, text message, end of input."""
    await stream.input_stream.send(
        ChatInputStreamConfigurationEvent(
            value=ConfigurationEvent(chat_mode="RETRIEVAL_MODE")
        )
    )

    await stream.input_stream.send(
        ChatInputStreamTextEvent(value=TextInputEvent(user_message="Hello"))
    )

    await stream.input_stream.send(
        ChatInputStreamEndOfInputEvent(value=EndOfInputEvent())
    )

    await stream.input_stream.close()


async def _receive_chat_output(
    stream: DuplexEventStream[ChatInputStream, ChatOutputStream, ChatOutput],
) -> tuple[bool, bool]:
    """Receive and validate chat output from the stream.

    Returns:
        Tuple of (got_text_events, got_metadata_event)
    """
    got_text_events = False
    got_metadata_event = False

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return got_text_events, got_metadata_event

    async for event in output_stream:
        if isinstance(event, ChatOutputStreamTextEvent):
            got_text_events = True
            assert event.value.system_message_type == "RESPONSE"
            assert event.value.conversation_id is not None
            assert event.value.user_message_id is not None
            assert event.value.system_message_id is not None
            assert event.value.system_message is not None
            assert isinstance(event.value.system_message, str)
            assert len(event.value.system_message) > 0
        elif isinstance(event, ChatOutputStreamMetadataEvent):
            got_metadata_event = True
            assert event.value.conversation_id is not None
            assert event.value.user_message_id is not None
            assert event.value.system_message_id is not None
            assert event.value.source_attributions is not None
            assert event.value.final_text_message is not None
            assert isinstance(event.value.final_text_message, str)
            assert len(event.value.final_text_message) > 0
        elif isinstance(event, ChatOutputStreamUnknown):
            pass
        else:
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(event).__name__}"
            )

    return got_text_events, got_metadata_event


async def test_chat_bidirectional_streaming(qbusiness_app: str) -> None:
    """Test bidirectional streaming with text input and chat output."""
    async with await create_qbusiness_client(
        REGION, transport=AWSCRTHTTPClient()
    ) as qbusiness_client:
        stream = await qbusiness_client.chat(
            application_id=qbusiness_app, client_token=str(uuid.uuid4())
        )

        results = await asyncio.gather(
            _send_chat_events(stream), _receive_chat_output(stream)
        )
        got_text_events, got_metadata_event = results[1]

        assert got_text_events, "Expected to receive text output events"
        assert got_metadata_event, "Expected to receive a metadata event"
