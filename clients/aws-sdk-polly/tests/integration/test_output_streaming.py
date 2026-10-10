# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test output streaming blob handling."""

from smithy_core.aio.utils import read_streaming_blob_async

from aws_sdk_polly.models import SynthesizeSpeechOutput

from . import (
    ENGINE,
    OUTPUT_FORMAT,
    REGION,
    SAMPLE_RATE,
    TEST_TEXT,
    VOICE_ID,
    create_polly_client,
)


async def test_synthesize_speech() -> None:
    """Test output-streaming SynthesizeSpeech operation."""
    async with await create_polly_client(REGION) as client:
        response = await client.synthesize_speech(
            engine=ENGINE,
            output_format=OUTPUT_FORMAT,
            sample_rate=SAMPLE_RATE,
            text=TEST_TEXT,
            voice_id=VOICE_ID,
        )

        assert isinstance(response, SynthesizeSpeechOutput)
        assert response.content_type == "audio/mpeg"
        assert response.request_characters == len(TEST_TEXT)

        audio = await read_streaming_blob_async(response.audio_stream)
        assert len(audio) > 0
