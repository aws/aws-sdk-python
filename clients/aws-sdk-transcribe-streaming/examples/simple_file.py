# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aiofile~=3.9.0",
#     "aws-sdk-transcribe-streaming[awscrt]",
# ]
#
# [tool.uv.sources]
# aws-sdk-transcribe-streaming = { path = "../" }
# ///
"""
Audio file transcription example using AWS Transcribe Streaming.

This example demonstrates how to:
- Read audio from a pre-recorded file
- Stream audio to AWS Transcribe Streaming service with rate limiting
- Receive and display transcription results as they arrive

Prerequisites:
- AWS credentials configured (via environment variables)
- An audio file (default: test.wav in PCM format)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

Usage:
- `uv run simple_file.py`
"""

import asyncio
import time
from pathlib import Path

import aiofile
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

AWS_REGION = "us-west-2"
ENDPOINT_URI = f"https://transcribestreaming.{AWS_REGION}.amazonaws.com"

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHANNEL_NUMS = 1
AUDIO_PATH = Path(__file__).parent / "test.wav"
CHUNK_SIZE = 1024 * 8


async def apply_realtime_delay(
    audio_stream: EventPublisher[AudioStream],
    reader,
    bytes_per_sample: int,
    sample_rate: float,
    channel_nums: int,
) -> None:
    """Applies a delay when reading an audio file stream to simulate a real-time
    delay.
    """
    start_time = time.time()
    elapsed_audio_time = 0.0
    async for chunk in reader:
        await audio_stream.send(
            AudioStreamAudioEvent(value=AudioEvent(audio_chunk=chunk))
        )
        elapsed_audio_time += len(chunk) / (
            bytes_per_sample * sample_rate * channel_nums
        )
        # sleep to simulate real-time streaming
        wait_time = start_time + elapsed_audio_time - time.time()
        await asyncio.sleep(wait_time)


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
    # NOTE: For pre-recorded files longer than 5 minutes, the sent audio
    # chunks should be rate limited to match the realtime bitrate of the
    # audio stream to avoid signing issues.
    async with aiofile.AIOFile(AUDIO_PATH, "rb") as afp:
        reader = aiofile.Reader(afp, chunk_size=CHUNK_SIZE)
        await apply_realtime_delay(
            audio_stream, reader, BYTES_PER_SAMPLE, SAMPLE_RATE, CHANNEL_NUMS
        )

    await audio_stream.close()


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

        print("Transcribing audio from file...")
        print("===============================")

        # Run audio streaming and transcription handling concurrently
        await asyncio.gather(write_chunks(stream.input_stream), handler.handle_events())


if __name__ == "__main__":
    asyncio.run(main())
