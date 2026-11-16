# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live RDS integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_rds.aio.client import AsyncRDSClient
from aws_sdk_rds.aio.config import AsyncRDSConfig
from aws_sdk_rds.client import RDSClient
from aws_sdk_rds.config import RDSConfig

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_name(infix: str = "") -> str:
    return f"{NAME_PREFIX}{infix}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncRDSClient:
    config = await AsyncRDSConfig.resolve(region=REGION)
    return AsyncRDSClient(config=config)


def create_sync_client() -> RDSClient:
    config = RDSConfig.resolve(region=REGION)
    return RDSClient(config=config)
