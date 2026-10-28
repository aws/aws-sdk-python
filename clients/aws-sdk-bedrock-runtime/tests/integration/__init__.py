# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


from pathlib import Path

from smithy_aws_core.aio.config import AwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig

MODEL_ID = "global.amazon.nova-2-lite-v1:0"
BIDIRECTIONAL_MODEL_ID = "amazon.nova-2-sonic-v1:0"
MESSAGE = "Who created the Python programming language?"
AUDIO_FILE = Path(__file__).parent / "assets" / "test.pcm"


async def create_bedrock_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncBedrockRuntimeClient:
    """Helper to create an AsyncBedrockRuntimeClient for a given region."""
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://bedrock-runtime.{region}.amazonaws.com",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncBedrockRuntimeClient(
        config=await AsyncBedrockRuntimeConfig.resolve(**overrides)
    )
