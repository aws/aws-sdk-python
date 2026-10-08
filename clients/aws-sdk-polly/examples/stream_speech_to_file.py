#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "aws-sdk-polly[awscrt]",
# ]
#
# [tool.uv.sources]
# aws-sdk-polly = { path = "../" }
# ///
"""
Speech synthesis to a file using AWS Polly bidirectional streaming.

This example demonstrates how to:
- Send text to AWS Polly over a bidirectional streaming connection
- Receive synthesized audio chunks as they become available
- Write the synthesized audio to an MP3 file

Prerequisites:
- AWS credentials configured (via environment variables)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

Usage:
- `uv run stream_speech_to_file.py`
- `uv run stream_speech_to_file.py "Hello from Polly."`
- `cat story.txt | uv run stream_speech_to_file.py -`
- `uv run stream_speech_to_file.py --voice Ruth --output hello.mp3 "Hi."`
"""

import argparse
import asyncio
import sys
import textwrap
from pathlib import Path

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
    StartSpeechSynthesisStreamInput,
    TextEvent,
)

DEFAULT_REGION = "us-east-1"
DEFAULT_VOICE = "Matthew"
DEFAULT_OUTPUT_PATH = Path(__file__).parent / "output.mp3"

SAMPLE_RATE = 24000
TEXT_CHUNK_SIZE = 160

# A few sentences delivered as separate events to demonstrate incremental
# input — Polly will start producing audio as soon as the first event arrives.
DEFAULT_TEXT_CHUNKS = [
    "Hello! This audio was synthesized using the AWS SDK for Python v4.",
    "Polly's bidirectional streaming API returns audio as it is generated, ",
    "which makes it well suited for piping output from a streaming language model.",
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
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the MP3 output.",
    )
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


async def write_audio(
    output_stream: EventReceiver[StartSpeechSynthesisStreamEventStream],
    output_path: Path,
):
    bytes_written = 0
    with output_path.open("wb") as f:
        async for event in output_stream:
            if isinstance(event, StartSpeechSynthesisStreamEventStreamAudioEvent):
                if event.value.audio_chunk:
                    f.write(event.value.audio_chunk)
                    bytes_written += len(event.value.audio_chunk)

    print(f"Wrote {bytes_written} bytes of MP3 audio to {output_path}")


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
            input=StartSpeechSynthesisStreamInput(
                engine="generative",
                output_format="mp3",
                sample_rate=str(SAMPLE_RATE),
                voice_id=args.voice,
            )
        )

        _, output_stream = await stream.await_output()
        if output_stream is None:
            raise RuntimeError("Polly stream did not return an output stream")

        print("Synthesizing audio...")
        await asyncio.gather(
            send_text(stream.input_stream, text_chunks),
            write_audio(output_stream, args.output),
        )


if __name__ == "__main__":
    asyncio.run(main())
