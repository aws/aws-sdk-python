# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live EC2 integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_ec2.aio.client import AsyncEC2Client
from aws_sdk_ec2.aio.config import AsyncEC2Config
from aws_sdk_ec2.client import EC2Client
from aws_sdk_ec2.config import EC2Config
from aws_sdk_ec2.models import Tag
from smithy_core.exceptions import CallError

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"

PURPOSE_TAG = Tag(key="Purpose", value="IntegTest")

# EC2 models none of its NotFound or DependencyViolation codes, so the client raises the base CallError.
EVENTUAL_ERRORS = (CallError,)


def unique_name(infix: str = "") -> str:
    return f"{NAME_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncEC2Client:
    config = await AsyncEC2Config.resolve(region=REGION)
    return AsyncEC2Client(config=config)


def create_sync_client() -> EC2Client:
    config = EC2Config.resolve(region=REGION)
    return EC2Client(config=config)
