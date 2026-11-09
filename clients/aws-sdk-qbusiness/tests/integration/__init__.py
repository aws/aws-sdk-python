# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_qbusiness.aio.client import AsyncQBusinessClient
from aws_sdk_qbusiness.aio.config import AsyncQBusinessConfig
from smithy_aws_core.aio.config import AsyncAwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

REGION = "us-east-1"


async def create_qbusiness_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncQBusinessClient:
    """Helper to create an AsyncQBusinessClient for a given region."""
    overrides: AsyncAwsConfigOverrides = {
        "endpoint_uri": f"https://qbusiness.{region}.api.aws",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncQBusinessClient(config=await AsyncQBusinessConfig.resolve(**overrides))
