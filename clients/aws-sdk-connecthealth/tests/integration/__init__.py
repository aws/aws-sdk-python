# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

from smithy_aws_core.aio.config import AwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from aws_sdk_connecthealth.client import AsyncConnectHealthClient
from aws_sdk_connecthealth.config import AsyncConnectHealthConfig, Plugin

REGION = "us-east-1"
AUDIO_FILE = Path(__file__).parent / "assets" / "test.wav"


async def create_connecthealth_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncConnectHealthClient:
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://health-agent.{region}.api.aws",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncConnectHealthClient(
        config=await AsyncConnectHealthConfig.resolve(**overrides)
    )


def streaming_endpoint_plugin(region: str) -> Plugin:
    """Per-operation plugin that routes to the ``streaming.`` host prefix."""
    streaming_uri = f"https://streaming.health-agent.{region}.api.aws"

    def _plugin(config: AsyncConnectHealthConfig) -> None:
        config.endpoint_uri = streaming_uri

    return _plugin
