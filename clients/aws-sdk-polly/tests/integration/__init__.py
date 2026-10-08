# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from smithy_aws_core.config import AwsConfigOverrides
from smithy_aws_core.identity import EnvironmentCredentialsResolver
from smithy_http.aio.interfaces import HTTPClient

from aws_sdk_polly.client import AsyncPollyClient
from aws_sdk_polly.config import AsyncPollyConfig

REGION = "us-east-1"
VOICE_ID = "Matthew"
ENGINE = "generative"
OUTPUT_FORMAT = "mp3"
SAMPLE_RATE = "24000"
TEST_TEXT = "Hello from the AWS SDK for Python v4 Polly integration tests."


async def create_polly_client(
    region: str, *, transport: HTTPClient | None = None
) -> AsyncPollyClient:
    """Helper to create an AsyncPollyClient for a given region."""
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://polly.{region}.amazonaws.com",
        "region": region,
        "aws_credentials_identity_resolver": EnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncPollyClient(config=await AsyncPollyConfig.resolve(**overrides))
