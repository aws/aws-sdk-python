# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from smithy_aws_core.aio.config import AwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from aws_sdk_transcribe_streaming.client import AsyncTranscribeStreamingClient
from aws_sdk_transcribe_streaming.config import AsyncTranscribeStreamingConfig

AUDIO_FILE = Path(__file__).parent / "assets" / "test.wav"


async def create_transcribe_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncTranscribeStreamingClient:
    """Helper to create an AsyncTranscribeStreamingClient for a given region."""
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://transcribestreaming.{region}.amazonaws.com",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncTranscribeStreamingClient(
        config=await AsyncTranscribeStreamingConfig.resolve(**overrides)
    )
