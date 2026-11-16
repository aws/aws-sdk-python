# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live CloudFormation integration tests, written once and run in both sync and async modes."""

import json
import uuid

from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.aio.config import AsyncCloudFormationConfig
from aws_sdk_cloudformation.client import CloudFormationClient
from aws_sdk_cloudformation.config import CloudFormationConfig
from aws_sdk_cloudformation.models import DescribeStacksInput, Stack
from waiters import wait_until

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
STACK_PREFIX = "aws-sdk-python-integ-"

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

# A fifo-suffixed name without FifoQueue=true is rejected by SQS during creation.
FAILING_TEMPLATE = json.dumps(
    {
        "Resources": {
            "Queue": {
                "Type": "AWS::SQS::Queue",
                "Properties": {"QueueName": "aws-sdk-python-integ-invalid.fifo"},
            }
        }
    }
)


def unique_stack_name() -> str:
    return f"{STACK_PREFIX}{uuid.uuid4().hex[:16]}"


async def create_async_client() -> AsyncCloudFormationClient:
    config = await AsyncCloudFormationConfig.resolve(region=REGION)
    return AsyncCloudFormationClient(config=config)


def create_sync_client() -> CloudFormationClient:
    config = CloudFormationConfig.resolve(region=REGION)
    return CloudFormationClient(config=config)


async def wait_for_stack_status(
    client: AsyncCloudFormationClient, stack_id: str, target: str, timeout: float = 600
) -> Stack:
    """Wait for the stack to reach ``target``, failing at once on any other settled status."""

    async def describe() -> Stack:
        output = await client.describe_stacks(DescribeStacksInput(stack_name=stack_id))
        assert output.stacks
        return output.stacks[0]

    def reached_target(stack: Stack) -> bool:
        status = stack.stack_status or ""
        if status == target:
            return True
        assert status.endswith("_IN_PROGRESS"), (
            f"stack reached {status}: {stack.stack_status_reason}"
        )
        return False

    return await wait_until(describe, reached_target, interval=3, timeout=timeout)
