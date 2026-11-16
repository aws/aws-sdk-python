# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live STS integration tests, written once and run in both sync and async modes."""

from aws_sdk_sts.aio.client import AsyncSTSClient
from aws_sdk_sts.aio.config import AsyncSTSConfig
from aws_sdk_sts.client import STSClient
from aws_sdk_sts.config import STSConfig
from smithy_aws_core.aio.identity import AsyncStaticCredentialsResolver
from smithy_aws_core.identity import AWSCredentialsIdentity, StaticCredentialsResolver

REGION = "us-west-2"


async def create_async_client(
    credentials: AWSCredentialsIdentity | None = None,
) -> AsyncSTSClient:
    """Create a client on the default credential chain, or on ``credentials`` when given."""
    if credentials is None:
        config = await AsyncSTSConfig.resolve(region=REGION)
    else:
        config = await AsyncSTSConfig.resolve(
            region=REGION,
            aws_credentials_identity_resolver=AsyncStaticCredentialsResolver(
                credentials
            ),
        )
    return AsyncSTSClient(config=config)


def create_sync_client(credentials: AWSCredentialsIdentity | None = None) -> STSClient:
    """Create a client on the default credential chain, or on ``credentials`` when given."""
    if credentials is None:
        config = STSConfig.resolve(region=REGION)
    else:
        config = STSConfig.resolve(
            region=REGION,
            aws_credentials_identity_resolver=StaticCredentialsResolver(credentials),
        )
    return STSClient(config=config)
