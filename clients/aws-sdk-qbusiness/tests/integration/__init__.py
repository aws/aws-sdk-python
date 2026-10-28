# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from smithy_aws_core.aio.config import AwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from aws_sdk_qbusiness.client import AsyncQBusinessClient
from aws_sdk_qbusiness.config import AsyncQBusinessConfig

REGION = "us-east-1"


async def create_qbusiness_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncQBusinessClient:
    """Helper to create an AsyncQBusinessClient for a given region."""
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://qbusiness.{region}.api.aws",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncQBusinessClient(config=await AsyncQBusinessConfig.resolve(**overrides))
