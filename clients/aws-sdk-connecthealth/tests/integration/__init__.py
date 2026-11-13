# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from aws_sdk_connecthealth.aio.client import AsyncConnectHealthClient
from aws_sdk_connecthealth.aio.config import AsyncConnectHealthConfig
from smithy_aws_core.aio.config import AsyncAwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

REGION = "us-east-1"
AUDIO_FILE = Path(__file__).parent / "assets" / "test.wav"

# (domain_id, subscription_id, output_s3_uri)
type ConnectHealthResources = tuple[str, str, str]


async def create_connecthealth_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncConnectHealthClient:
    overrides: AsyncAwsConfigOverrides = {
        "endpoint_uri": f"https://health-agent.{region}.api.aws",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncConnectHealthClient(
        config=await AsyncConnectHealthConfig.resolve(**overrides)
    )
