# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional streaming event stream handling."""

import asyncio
import uuid

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_lex_runtime_v2.models import (
    ConfigurationEvent,
    DisconnectionEvent,
    StartConversationOutput,
    StartConversationRequestEventStream,
    StartConversationRequestEventStreamConfigurationEvent,
    StartConversationRequestEventStreamDisconnectionEvent,
    StartConversationRequestEventStreamTextInputEvent,
    StartConversationResponseEventStream,
    StartConversationResponseEventStreamHeartbeatEvent,
    StartConversationResponseEventStreamIntentResultEvent,
    StartConversationResponseEventStreamTextResponseEvent,
    StartConversationResponseEventStreamTranscriptEvent,
    TextInputEvent,
)

from . import BOT_ALIAS_ID, LOCALE_ID, REGION, create_lex_client


async def _send_events(
    stream: DuplexEventStream[
        StartConversationRequestEventStream,
        StartConversationResponseEventStream,
        StartConversationOutput,
    ],
) -> None:
    """Send configuration, text input, and disconnection events."""
    input_stream = stream.input_stream

    await input_stream.send(
        StartConversationRequestEventStreamConfigurationEvent(
            value=ConfigurationEvent(response_content_type="text/plain; charset=utf-8")
        )
    )

    await input_stream.send(
        StartConversationRequestEventStreamTextInputEvent(
            value=TextInputEvent(text="Hello")
        )
    )

    await asyncio.sleep(3)

    await input_stream.send(
        StartConversationRequestEventStreamDisconnectionEvent(
            value=DisconnectionEvent()
        )
    )

    await input_stream.close()


async def _receive_events(
    stream: DuplexEventStream[
        StartConversationRequestEventStream,
        StartConversationResponseEventStream,
        StartConversationOutput,
    ],
) -> tuple[bool, bool, bool, bool]:
    """Receive and collect output from the stream.

    Returns:
        Tuple of (got_transcript, got_intent_result, got_text_response, got_heartbeat)
    """
    got_transcript = False
    got_intent_result = False
    got_text_response = False
    got_heartbeat = False

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return got_transcript, got_intent_result, got_text_response, got_heartbeat

    async for event in output_stream:
        if isinstance(event, StartConversationResponseEventStreamTranscriptEvent):
            got_transcript = True
            assert event.value.event_id is not None
            assert event.value.transcript == "Hello"
        elif isinstance(event, StartConversationResponseEventStreamIntentResultEvent):
            got_intent_result = True
            assert event.value.event_id is not None
            assert event.value.input_mode == "Text"
            assert event.value.session_id is not None
            assert event.value.session_state is not None
            assert event.value.session_state.intent is not None
            assert event.value.session_state.intent.name == "Greeting"
            assert event.value.session_state.intent.state == "Fulfilled"
            assert event.value.interpretations is not None
            assert len(event.value.interpretations) == 2
            interps_by_name = {
                i.intent.name: i for i in event.value.interpretations if i.intent
            }
            assert "Greeting" in interps_by_name
            assert "FallbackIntent" in interps_by_name
            assert interps_by_name["Greeting"].nlu_confidence is not None
            assert interps_by_name["Greeting"].nlu_confidence.score == 1.0
        elif isinstance(event, StartConversationResponseEventStreamTextResponseEvent):
            got_text_response = True
            assert event.value.event_id is not None
            assert event.value.messages is not None
            assert len(event.value.messages) == 1
            msg = event.value.messages[0]
            assert msg.content_type == "PlainText"
            assert msg.content == "Hello! How can I help you?"
        elif isinstance(event, StartConversationResponseEventStreamHeartbeatEvent):
            got_heartbeat = True
            assert event.value.event_id is not None
        else:
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(event).__name__}"
            )

    return got_transcript, got_intent_result, got_text_response, got_heartbeat


async def test_start_conversation(lex_bot: str) -> None:
    """Test bidirectional streaming StartConversation operation."""
    async with await create_lex_client(REGION, transport=AWSCRTHTTPClient()) as client:
        stream = await client.start_conversation(
            bot_id=lex_bot,
            bot_alias_id=BOT_ALIAS_ID,
            locale_id=LOCALE_ID,
            session_id=str(uuid.uuid4()),
            conversation_mode="TEXT",
        )

        results = await asyncio.gather(_send_events(stream), _receive_events(stream))

        got_transcript, got_intent_result, got_text_response, got_heartbeat = results[1]
        assert got_transcript, "Expected to receive a TranscriptEvent"
        assert got_intent_result, "Expected to receive an IntentResultEvent"
        assert got_text_response, "Expected to receive a TextResponseEvent"
        assert got_heartbeat, "Expected to receive a HeartbeatEvent"
