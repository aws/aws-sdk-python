# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from smithy_aws_core.aio.config import AwsConfigOverrides
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver
from smithy_http.aio.interfaces import AsyncHTTPClient

from aws_sdk_lex_runtime_v2.client import AsyncLexRuntimeV2Client
from aws_sdk_lex_runtime_v2.config import AsyncLexRuntimeV2Config

BOT_ALIAS_ID = "TSTALIASID"
LOCALE_ID = "en_US"
REGION = "us-east-1"


async def create_lex_client(
    region: str, *, transport: AsyncHTTPClient | None = None
) -> AsyncLexRuntimeV2Client:
    overrides: AwsConfigOverrides = {
        "endpoint_uri": f"https://runtime-v2-lex.{region}.amazonaws.com",
        "region": region,
        "aws_credentials_identity_resolver": AsyncEnvironmentCredentialsResolver(),
    }
    if transport is not None:
        overrides["transport"] = transport
    return AsyncLexRuntimeV2Client(
        config=await AsyncLexRuntimeV2Config.resolve(**overrides)
    )
