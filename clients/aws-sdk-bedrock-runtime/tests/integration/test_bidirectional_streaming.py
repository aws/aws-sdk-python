# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test bidirectional streaming duplex event stream handling."""

import asyncio
import base64
import json
import uuid

from smithy_core.aio.eventstream import DuplexEventStream
from smithy_http.aio.crt import AWSCRTHTTPClient

from aws_sdk_bedrock_runtime.models import (
    BidirectionalInputPayloadPart,
    InvokeModelWithBidirectionalStreamInputChunk,
    InvokeModelWithBidirectionalStreamInput,
    InvokeModelWithBidirectionalStreamOutput,
    InvokeModelWithBidirectionalStreamOperationOutput,
    InvokeModelWithBidirectionalStreamOutputChunk,
)

from . import AUDIO_FILE, BIDIRECTIONAL_MODEL_ID, create_bedrock_client

CHUNK_SIZE = 512
SILENCE_CHUNKS = 125
RESPONSE_WAIT_TIME = 3

DEFAULT_SYSTEM_PROMPT = (
    "You are a friendly assistant. Keep your responses short, "
    "generally one or two sentences."
)

START_SESSION_EVENT = """{
    "event": {
        "sessionStart": {
            "inferenceConfiguration": {
                "maxTokens": 1024,
                "topP": 0.9,
                "temperature": 0.7
            }
        }
    }
}"""

START_PROMPT_EVENT = """{
    "event": {
        "promptStart": {
            "promptName": "%s",
            "textOutputConfiguration": {
                "mediaType": "text/plain"
            },
            "audioOutputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": 24000,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "voiceId": "matthew",
                "encoding": "base64",
                "audioType": "SPEECH"
            }
        }
    }
}"""

TEXT_CONTENT_START_EVENT = """{
    "event": {
        "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "type": "TEXT",
            "interactive": true,
            "role": "%s",
            "textInputConfiguration": {
                "mediaType": "text/plain"
            }
        }
    }
}"""

TEXT_INPUT_EVENT = """{
    "event": {
        "textInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
        }
    }
}"""

CONTENT_END_EVENT = """{
    "event": {
        "contentEnd": {
            "promptName": "%s",
            "contentName": "%s"
        }
    }
}"""

AUDIO_CONTENT_START_EVENT = """{
    "event": {
        "contentStart": {
            "promptName": "%s",
            "contentName": "%s",
            "type": "AUDIO",
            "interactive": true,
            "role": "USER",
            "audioInputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": 16000,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "audioType": "SPEECH",
                "encoding": "base64"
            }
        }
    }
}"""

AUDIO_INPUT_EVENT = """{
    "event": {
        "audioInput": {
            "promptName": "%s",
            "contentName": "%s",
            "content": "%s"
        }
    }
}"""

PROMPT_END_EVENT = """{
    "event": {
        "promptEnd": {
            "promptName": "%s"
        }
    }
}"""

SESSION_END_EVENT = """{
    "event": {
        "sessionEnd": {}
    }
}"""


async def _send_event(
    stream: DuplexEventStream[
        InvokeModelWithBidirectionalStreamInput,
        InvokeModelWithBidirectionalStreamOutput,
        InvokeModelWithBidirectionalStreamOperationOutput,
    ],
    event_json: str,
) -> None:
    """Send a raw event JSON string to the Bedrock stream."""
    event = InvokeModelWithBidirectionalStreamInputChunk(
        value=BidirectionalInputPayloadPart(bytes_=event_json.encode("utf-8"))
    )
    await stream.input_stream.send(event)


async def _send_audio_chunks(
    stream: DuplexEventStream[
        InvokeModelWithBidirectionalStreamInput,
        InvokeModelWithBidirectionalStreamOutput,
        InvokeModelWithBidirectionalStreamOperationOutput,
    ],
    prompt_name: str,
    audio_content_name: str,
) -> None:
    """Send audio chunks from file simulating real-time delay."""
    chunk_count = 0
    with AUDIO_FILE.open("rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            chunk_count += 1
            encoded_chunk = base64.b64encode(chunk).decode("utf-8")
            await _send_event(
                stream,
                AUDIO_INPUT_EVENT % (prompt_name, audio_content_name, encoded_chunk),
            )
            # 512 bytes / (16000 Hz * 2 bytes/sample) = 0.016s per chunk
            await asyncio.sleep(0.016)

    assert chunk_count > 0, f"No audio chunks were sent from {AUDIO_FILE}"

    silence_chunk = bytes(CHUNK_SIZE)
    encoded_silence = base64.b64encode(silence_chunk).decode("utf-8")
    for _ in range(SILENCE_CHUNKS):
        await _send_event(
            stream,
            AUDIO_INPUT_EVENT % (prompt_name, audio_content_name, encoded_silence),
        )
        await asyncio.sleep(0.016)

    await _send_event(stream, CONTENT_END_EVENT % (prompt_name, audio_content_name))
    await asyncio.sleep(RESPONSE_WAIT_TIME)
    await _send_event(stream, PROMPT_END_EVENT % prompt_name)
    await _send_event(stream, SESSION_END_EVENT)


async def _receive_stream_output(
    stream: DuplexEventStream[
        InvokeModelWithBidirectionalStreamInput,
        InvokeModelWithBidirectionalStreamOutput,
        InvokeModelWithBidirectionalStreamOperationOutput,
    ],
) -> tuple[bool, bool, list[str]]:
    """Receive and collect output from the bidirectional stream.

    Returns:
        Tuple of (got_text, got_audio, all_text_output)
    """
    got_text = False
    got_audio = False
    all_text_output: list[str] = []

    await stream.await_output()
    output_stream = stream.output_stream
    if output_stream is None:
        return got_text, got_audio, all_text_output

    async for out in output_stream:
        if not isinstance(out, InvokeModelWithBidirectionalStreamOutputChunk):
            raise RuntimeError(
                f"Received unexpected event type in stream: {type(out).__name__}"
            )

        payload = out.value.bytes_
        if not payload:
            continue

        msg = json.loads(payload.decode("utf-8"))
        event_data = msg.get("event", {})

        if "textOutput" in event_data:
            got_text = True
            text_content = event_data["textOutput"].get("content", "")
            all_text_output.append(text_content)
        if "audioOutput" in event_data:
            got_audio = True
        if "completionEnd" in event_data:
            break

    return got_text, got_audio, all_text_output


async def test_invoke_model_with_bidirectional_stream() -> None:
    """Test bidirectional streaming with audio input and text/audio output."""
    async with await create_bedrock_client(
        "us-east-1", transport=AWSCRTHTTPClient()
    ) as bedrock_client:
        stream = await bedrock_client.invoke_model_with_bidirectional_stream(
            model_id=BIDIRECTIONAL_MODEL_ID
        )

        prompt_name = str(uuid.uuid4())
        content_name = str(uuid.uuid4())
        audio_content_name = str(uuid.uuid4())

        init_events = [
            START_SESSION_EVENT,
            START_PROMPT_EVENT % prompt_name,
            TEXT_CONTENT_START_EVENT % (prompt_name, content_name, "SYSTEM"),
            TEXT_INPUT_EVENT % (prompt_name, content_name, DEFAULT_SYSTEM_PROMPT),
            CONTENT_END_EVENT % (prompt_name, content_name),
        ]

        for event in init_events:
            await _send_event(stream, event)

        await _send_event(
            stream, AUDIO_CONTENT_START_EVENT % (prompt_name, audio_content_name)
        )

        results = await asyncio.gather(
            _send_audio_chunks(stream, prompt_name, audio_content_name),
            _receive_stream_output(stream),
        )
        got_text, got_audio, all_text_output = results[1]

        assert got_text, "Expected to receive text output"
        assert got_audio, "Expected to receive audio output"
        assert len(all_text_output) > 0, "Expected non-empty text output"
