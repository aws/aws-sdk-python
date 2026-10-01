# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional streaming event stream handling."""

import asyncio

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_polly.models import (
    CloseStreamEvent,
    StartSpeechSynthesisStreamActionStream,
    StartSpeechSynthesisStreamActionStreamCloseStreamEvent,
    StartSpeechSynthesisStreamActionStreamTextEvent,
    StartSpeechSynthesisStreamEventStream,
    StartSpeechSynthesisStreamEventStreamAudioEvent,
    StartSpeechSynthesisStreamEventStreamServiceFailureException,
    StartSpeechSynthesisStreamEventStreamServiceQuotaExceededException,
    StartSpeechSynthesisStreamEventStreamStreamClosedEvent,
    StartSpeechSynthesisStreamEventStreamThrottlingException,
    StartSpeechSynthesisStreamEventStreamUnknown,
    StartSpeechSynthesisStreamEventStreamValidationException,
    StartSpeechSynthesisStreamOutput,
    TextEvent,
)

from . import (
    ENGINE,
    OUTPUT_FORMAT,
    REGION,
    SAMPLE_RATE,
    TEST_TEXT,
    VOICE_ID,
    create_polly_client,
)

ERROR_EVENT_TYPES = (
    StartSpeechSynthesisStreamEventStreamValidationException,
    StartSpeechSynthesisStreamEventStreamServiceQuotaExceededException,
    StartSpeechSynthesisStreamEventStreamServiceFailureException,
    StartSpeechSynthesisStreamEventStreamThrottlingException,
)


async def _send_text(
    stream: DuplexEventStream[
        StartSpeechSynthesisStreamActionStream,
        StartSpeechSynthesisStreamEventStream,
        StartSpeechSynthesisStreamOutput,
    ],
) -> None:
    """Send text input and close the input stream."""
    await stream.input_stream.send(
        StartSpeechSynthesisStreamActionStreamTextEvent(value=TextEvent(text=TEST_TEXT))
    )
    await stream.input_stream.send(
        StartSpeechSynthesisStreamActionStreamCloseStreamEvent(CloseStreamEvent())
    )
    await stream.input_stream.close()


async def _receive_audio(
    stream: DuplexEventStream[
        StartSpeechSynthesisStreamActionStream,
        StartSpeechSynthesisStreamEventStream,
        StartSpeechSynthesisStreamOutput,
    ],
) -> tuple[int, int | None]:
    """Receive synthesized audio and the final stream summary."""
    audio_bytes = 0
    request_characters: int | None = None

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return audio_bytes, request_characters

    async for event in output_stream:
        if isinstance(event, StartSpeechSynthesisStreamEventStreamAudioEvent):
            if event.value.audio_chunk:
                audio_bytes += len(event.value.audio_chunk)
        elif isinstance(event, StartSpeechSynthesisStreamEventStreamStreamClosedEvent):
            request_characters = event.value.request_characters
            break
        elif isinstance(event, ERROR_EVENT_TYPES):
            raise event.value
        elif isinstance(event, StartSpeechSynthesisStreamEventStreamUnknown):
            raise RuntimeError(f"Received unknown event in stream: {event.tag}")
        else:
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(event).__name__}"
            )

    return audio_bytes, request_characters


async def test_start_speech_synthesis_stream() -> None:
    """Test bidirectional streaming with text input and audio output."""
    async with await create_polly_client(
        REGION, transport=AWSCRTHTTPClient()
    ) as client:
        stream = await client.start_speech_synthesis_stream(
            engine=ENGINE,
            output_format=OUTPUT_FORMAT,
            sample_rate=SAMPLE_RATE,
            voice_id=VOICE_ID,
        )

        results = await asyncio.gather(_send_text(stream), _receive_audio(stream))
        audio_bytes, request_characters = results[1]

        assert audio_bytes > 0, "Expected to receive synthesized audio"
        assert request_characters == len(TEST_TEXT)
