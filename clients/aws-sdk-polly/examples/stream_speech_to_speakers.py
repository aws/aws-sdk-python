#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aws-sdk-polly[awscrt]",
#     "miniaudio~=1.71",
# ]
#
# [tool.uv.sources]
# aws-sdk-polly = { path = "../" }
# ///
"""
Real-time MP3 speech synthesis playback using AWS Polly bidirectional
streaming.

This example demonstrates how to:
- Send text to AWS Polly over a bidirectional streaming connection
- Receive MP3 audio chunks as they become available
- Decode and play the MP3 stream with miniaudio

Prerequisites:
- AWS credentials configured (via environment variables)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

Usage:
- `uv run stream_speech_to_speakers.py`
- `uv run stream_speech_to_speakers.py "Hello from Polly."`
- `cat story.txt | uv run stream_speech_to_speakers.py -`
- `uv run stream_speech_to_speakers.py --voice Ruth "Hi."`
"""

import argparse
import asyncio
import sys
import textwrap
import threading
from collections import deque

import miniaudio
from smithy_aws_core.identity import EnvironmentCredentialsResolver
from smithy_core.aio.interfaces.eventstream import EventPublisher, EventReceiver
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_polly.client import AsyncPollyClient
from aws_sdk_polly.config import AsyncPollyConfig
from aws_sdk_polly.models import (
    CloseStreamEvent,
    StartSpeechSynthesisStreamActionStream,
    StartSpeechSynthesisStreamActionStreamCloseStreamEvent,
    StartSpeechSynthesisStreamActionStreamTextEvent,
    StartSpeechSynthesisStreamEventStream,
    StartSpeechSynthesisStreamEventStreamAudioEvent,
    StartSpeechSynthesisStreamEventStreamStreamClosedEvent,
    TextEvent,
)

DEFAULT_REGION = "us-east-1"
DEFAULT_VOICE = "Matthew"

SAMPLE_RATE = 24000
TEXT_CHUNK_SIZE = 160
CHANNELS = 1
FRAMES_TO_READ = 1024
DEVICE_BUFFER_MS = 100

# Each entry simulates a piece of text arriving incrementally, for example,
# tokens streamed from a language model. Polly begins generating audio as soon
# as the first event arrives.
DEFAULT_TEXT_CHUNKS = [
    "Hello! ",
    "This MP3 audio is being streamed through miniaudio in real time ",
    "as Polly synthesizes it. ",
    "Each piece of text is sent as a separate event over a bidirectional stream.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "text", nargs="?", help='Text to synthesize. Use "-" to read text from stdin.'
    )
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Polly voice ID.")
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region.")
    return parser.parse_args()


def chunk_text(text: str) -> list[str]:
    chunks = textwrap.wrap(text, width=TEXT_CHUNK_SIZE, break_long_words=False)
    return [f"{chunk} " for chunk in chunks[:-1]] + chunks[-1:]


def get_text_chunks(text_arg: str | None) -> list[str]:
    if text_arg is None:
        return DEFAULT_TEXT_CHUNKS

    text = sys.stdin.read() if text_arg == "-" else text_arg
    if not text.strip():
        raise SystemExit("No text provided.")
    return chunk_text(text)


async def send_text(
    input_stream: EventPublisher[StartSpeechSynthesisStreamActionStream],
    text_chunks: list[str],
):
    for chunk in text_chunks:
        await input_stream.send(
            StartSpeechSynthesisStreamActionStreamTextEvent(value=TextEvent(text=chunk))
        )

    # Signal the end of input so Polly flushes the final audio.
    await input_stream.send(
        StartSpeechSynthesisStreamActionStreamCloseStreamEvent(CloseStreamEvent())
    )
    await input_stream.close()


class Mp3StreamSource:
    """A thread-safe blocking byte stream for miniaudio's MP3 decoder."""

    def __init__(self):
        self.ffi_handle = None
        self.error_in_readcallback = None
        self._chunks: deque[bytes] = deque()
        self._buffered = 0
        self._closed = False
        self._lock = threading.Condition()

    def write(self, data: bytes):
        with self._lock:
            self._chunks.append(data)
            self._buffered += len(data)
            self._lock.notify_all()

    def read(self, num_bytes: int) -> bytes:
        with self._lock:
            # Block only when nothing is buffered. Returning partial reads lets
            # the decoder start as soon as the first audio chunk arrives,
            # instead of waiting for `num_bytes` worth of MP3 data to accumulate.
            while self._buffered == 0 and not self._closed:
                self._lock.wait()

            if self._buffered == 0 and self._closed:
                return b""

            out = bytearray()
            while num_bytes > 0 and self._chunks:
                head = self._chunks[0]
                if len(head) <= num_bytes:
                    out.extend(head)
                    num_bytes -= len(head)
                    self._buffered -= len(head)
                    self._chunks.popleft()
                else:
                    out.extend(head[:num_bytes])
                    self._chunks[0] = head[num_bytes:]
                    self._buffered -= num_bytes
                    num_bytes = 0
            return bytes(out)

    def seek(self, offset, origin) -> bool:
        return False

    def close(self):
        with self._lock:
            self._closed = True
            self._lock.notify_all()


def run_player(source: Mp3StreamSource, stop: threading.Event, errors: list[Exception]):
    try:
        stream = miniaudio.stream_any(
            source,
            source_format=miniaudio.FileFormat.MP3,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            frames_to_read=FRAMES_TO_READ,
        )
        next(stream)

        with miniaudio.PlaybackDevice(
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            buffersize_msec=DEVICE_BUFFER_MS,
        ) as device:
            device.start(stream)
            while not stop.is_set() and device.callback_generator is not None:
                stop.wait(0.05)
    except Exception as exc:
        errors.append(exc)


def raise_player_error(errors: list[Exception]):
    if errors:
        raise RuntimeError("MP3 playback failed") from errors[0]


async def wait_until_player_stops_or_errors(
    player_thread: threading.Thread, errors: list[Exception]
) -> None:
    while player_thread.is_alive():
        raise_player_error(errors)
        await asyncio.to_thread(player_thread.join, 0.1)

    raise_player_error(errors)


async def play_audio(
    output_stream: EventReceiver[StartSpeechSynthesisStreamEventStream],
):
    source = Mp3StreamSource()
    stop_player = threading.Event()
    player_errors: list[Exception] = []
    player_thread = threading.Thread(
        target=run_player, args=(source, stop_player, player_errors), daemon=True
    )
    player_thread.start()

    try:
        async for event in output_stream:
            raise_player_error(player_errors)
            if isinstance(event, StartSpeechSynthesisStreamEventStreamAudioEvent):
                if event.value.audio_chunk:
                    source.write(event.value.audio_chunk)
            elif isinstance(
                event, StartSpeechSynthesisStreamEventStreamStreamClosedEvent
            ):
                break
    finally:
        source.close()
        await wait_until_player_stops_or_errors(player_thread, player_errors)


async def main():
    args = parse_args()
    text_chunks = get_text_chunks(args.text)

    async with AsyncPollyClient(
        config=await AsyncPollyConfig.resolve(
            endpoint_uri=f"https://polly.{args.region}.amazonaws.com",
            region=args.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            transport=AWSCRTHTTPClient(),
        )
    ) as client:
        stream = await client.start_speech_synthesis_stream(
            engine="generative",
            output_format="mp3",
            sample_rate=str(SAMPLE_RATE),
            voice_id=args.voice,
        )

        _, output_stream = await stream.await_output()

        print("Streaming MP3 audio to speakers...")
        await asyncio.gather(
            send_text(stream.input_stream, text_chunks), play_audio(output_stream)
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)
