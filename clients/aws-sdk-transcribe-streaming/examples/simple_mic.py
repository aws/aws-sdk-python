# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aws-sdk-transcribe-streaming[awscrt]",
#     "sounddevice~=0.5.3",
# ]
#
# [tool.uv.sources]
# aws-sdk-transcribe-streaming = { path = "../" }
# ///
"""
Real-time audio transcription example using AWS Transcribe Streaming.

This example demonstrates how to:
- Stream audio from your microphone in real-time
- Send audio to AWS Transcribe Streaming service
- Receive and display transcription results as they arrive

Prerequisites:
- AWS credentials configured (via environment variables)
- A working microphone
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

Usage:
- `uv run simple_mic.py`
"""

import asyncio
import sys
from typing import Any, AsyncGenerator, Tuple

import sounddevice
from smithy_aws_core.identity import EnvironmentCredentialsResolver
from smithy_core.aio.interfaces.eventstream import EventPublisher, EventReceiver
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_transcribe_streaming.client import AsyncTranscribeStreamingClient
from aws_sdk_transcribe_streaming.config import AsyncTranscribeStreamingConfig
from aws_sdk_transcribe_streaming.models import (
    AudioEvent,
    AudioStream,
    AudioStreamAudioEvent,
    TranscriptEvent,
    TranscriptResultStream,
)

# Configuration
AWS_REGION = "us-west-2"
ENDPOINT_URI = f"https://transcribestreaming.{AWS_REGION}.amazonaws.com"
SAMPLE_RATE = 16000


async def mic_stream() -> AsyncGenerator[Tuple[bytes, Any], None]:
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue: asyncio.Queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=SAMPLE_RATE,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
    )

    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status


class TranscriptResultStreamHandler:
    def __init__(self, stream: EventReceiver[TranscriptResultStream]):
        self.stream = stream

    async def handle_events(self):
        # Continuously receives events from the stream and delegates
        # to appropriate handlers based on event type.
        async for event in self.stream:
            if isinstance(event.value, TranscriptEvent):
                await self.handle_transcript_event(event.value)

    async def handle_transcript_event(self, event: TranscriptEvent):
        # This handler can be implemented to handle transcriptions as needed.
        # Here's an example to get started.
        if not event.transcript or not event.transcript.results:
            return

        results = event.transcript.results
        for result in results:
            if result.alternatives:
                for alt in result.alternatives:
                    print(alt.transcript)


async def write_chunks(audio_stream: EventPublisher[AudioStream]):
    # This connects the raw audio chunks generator coming from the microphone
    # and passes them along to the transcription stream.
    async for chunk, _ in mic_stream():
        await audio_stream.send(
            AudioStreamAudioEvent(value=AudioEvent(audio_chunk=chunk))
        )


async def main():
    # Initialize the Transcribe Streaming client
    async with AsyncTranscribeStreamingClient(
        config=await AsyncTranscribeStreamingConfig.resolve(
            endpoint_uri=ENDPOINT_URI,
            region=AWS_REGION,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            transport=AWSCRTHTTPClient(),
        )
    ) as client:
        # Start a streaming transcription session
        stream = await client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hertz=SAMPLE_RATE,
            media_encoding="pcm",
        )

        # Get the output stream for receiving transcription results
        _, output_stream = await stream.await_output()

        # Set up the handler for processing transcription events
        handler = TranscriptResultStreamHandler(output_stream)

        print("Start talking to see transcription!")
        print("(Press Ctrl+C to stop)")
        print("===================================")

        # Run audio streaming and transcription handling concurrently
        await asyncio.gather(write_chunks(stream.input_stream), handler.handle_events())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
