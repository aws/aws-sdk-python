# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional event stream handling."""

import asyncio
import time

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_transcribe_streaming.models import (
    AudioEvent,
    AudioStream,
    AudioStreamAudioEvent,
    LanguageCode,
    MediaEncoding,
    StartStreamTranscriptionOutput,
    TranscriptResultStream,
    TranscriptResultStreamTranscriptEvent,
)

from . import AUDIO_FILE, create_transcribe_client

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1
CHUNK_SIZE = 1024 * 8


async def _send_audio_chunks(
    stream: DuplexEventStream[
        AudioStream, TranscriptResultStream, StartStreamTranscriptionOutput
    ],
) -> None:
    """Send audio chunks from file simulating real-time delay."""
    start_time = time.time()
    elapsed_audio_time = 0.0

    with AUDIO_FILE.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            await stream.input_stream.send(
                AudioStreamAudioEvent(value=AudioEvent(audio_chunk=chunk))
            )
            elapsed_audio_time += len(chunk) / (
                BYTES_PER_SAMPLE * SAMPLE_RATE * CHANNEL_NUMS
            )
            wait_time = start_time + elapsed_audio_time - time.time()
            await asyncio.sleep(wait_time)

    await stream.input_stream.close()


async def _receive_transcription_output(
    stream: DuplexEventStream[
        AudioStream, TranscriptResultStream, StartStreamTranscriptionOutput
    ],
) -> tuple[bool, list[str]]:
    """Receive and collect transcription output from the stream.

    Returns:
        Tuple of (got_transcript_events, transcripts)
    """
    got_transcript_events = False
    transcripts: list[str] = []

    _, output_stream = await stream.await_output()
    if output_stream is None:
        return got_transcript_events, transcripts

    async for event in output_stream:
        if not isinstance(event, TranscriptResultStreamTranscriptEvent):
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(event).__name__}"
            )

        got_transcript_events = True
        if event.value.transcript and event.value.transcript.results:
            for result in event.value.transcript.results:
                if result.alternatives:
                    for alt in result.alternatives:
                        if alt.transcript:
                            transcripts.append(alt.transcript)

    return got_transcript_events, transcripts


async def test_start_stream_transcription() -> None:
    """Test bidirectional streaming with audio input and transcription output."""
    async with await create_transcribe_client(
        "us-west-2", transport=AWSCRTHTTPClient()
    ) as transcribe_client:
        stream = await transcribe_client.start_stream_transcription(
            language_code=LanguageCode.EN_US,
            media_sample_rate_hertz=SAMPLE_RATE,
            media_encoding=MediaEncoding.PCM,
        )

        results = await asyncio.gather(
            _send_audio_chunks(stream), _receive_transcription_output(stream)
        )
        got_transcript_events, transcripts = results[1]

        assert got_transcript_events, "Expected to receive transcript events"
        assert len(transcripts) > 0, "Expected to receive at least one transcript"
