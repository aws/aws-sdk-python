# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live CloudFormation integration tests, written once and run in both sync and async modes.

Only calls that create no resources run here; the stack lifecycle is covered by
``tests/functional/test_stacks.py`` against recorded responses.
"""

import json

from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.aio.config import AsyncCloudFormationConfig
from aws_sdk_cloudformation.client import CloudFormationClient
from aws_sdk_cloudformation.config import CloudFormationConfig

REGION = "us-west-2"

QUEUE_TEMPLATE = json.dumps(
    {
        "Description": "aws-sdk-python integration test",
        "Parameters": {"Delay": {"Type": "Number", "Default": 0}},
        "Resources": {
            "Queue": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"DelaySeconds": {"Ref": "Delay"}},
            }
        },
        "Outputs": {"QueueUrl": {"Value": {"Ref": "Queue"}}},
    }
)


async def create_async_client() -> AsyncCloudFormationClient:
    config = await AsyncCloudFormationConfig.resolve(region=REGION)
    return AsyncCloudFormationClient(config=config)


def create_sync_client() -> CloudFormationClient:
    config = CloudFormationConfig.resolve(region=REGION)
    return CloudFormationClient(config=config)
