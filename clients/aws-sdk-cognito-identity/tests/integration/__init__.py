# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live Cognito Identity integration tests, run in both sync and async modes."""

import uuid

from aws_sdk_cognito_identity.aio.client import AsyncCognitoIdentityClient
from aws_sdk_cognito_identity.aio.config import AsyncCognitoIdentityConfig
from aws_sdk_cognito_identity.client import CognitoIdentityClient
from aws_sdk_cognito_identity.config import CognitoIdentityConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_name() -> str:
    return f"{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncCognitoIdentityClient:
    config = await AsyncCognitoIdentityConfig.resolve(region=REGION)
    return AsyncCognitoIdentityClient(config=config)


def create_sync_client() -> CognitoIdentityClient:
    config = CognitoIdentityConfig.resolve(region=REGION)
    return CognitoIdentityClient(config=config)
