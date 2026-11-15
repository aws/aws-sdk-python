# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

from aws_sdk_polly.models import DescribeVoicesOutput

from . import ENGINE, REGION, VOICE_ID, create_polly_client


async def test_describe_voices() -> None:
    """Test non-streaming DescribeVoices operation."""
    async with await create_polly_client(REGION) as client:
        response = await client.describe_voices(engine=ENGINE)

        assert isinstance(response, DescribeVoicesOutput)
        assert response.voices is not None
        assert len(response.voices) > 0

        voices_by_id = {voice.id: voice for voice in response.voices if voice.id}
        assert VOICE_ID in voices_by_id

        voice = voices_by_id[VOICE_ID]
        assert voice.language_code == "en-US"
        assert voice.supported_engines is not None
        assert ENGINE in voice.supported_engines
