# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stack lifecycle and validation, replayed from recordings of the live service.

Record against AWS with ``SMITHY_PYTHON_TEST_MODE=record pytest <this file>``.

The recordings are in ``recordings/<test function>/cloud_formation.py``. Each serves
both clients, because playback answers by operation and never looks at the request.
Stack names need a unique suffix, so a test compares only their prefix: the recording
holds the name it was recorded with.
"""

import json
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.aio.config import AsyncCloudFormationConfig
from aws_sdk_cloudformation.client import CloudFormationClient
from aws_sdk_cloudformation.config import CloudFormationConfig
from aws_sdk_cloudformation.models import Stack
from dual_mode import MODES, AwaitableClient, Mode
from smithy_test import instrument
from smithy_test.aio import instrument_async
from waiters import wait_until

REGION = "us-west-2"
RECORDING = os.environ.get("SMITHY_PYTHON_TEST_MODE") == "record"
# Playback answers at once, so there is nothing to wait for.
POLL_INTERVAL = 15 if RECORDING else 0

QUEUE_TEMPLATE = json.dumps(
    {
        "Description": "aws-sdk-python recorded test",
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
                "Properties": {"QueueName": "aws-sdk-python-recorded-invalid.fifo"},
            }
        }
    }
)


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def cloudformation(
    mode: Mode, request: pytest.FixtureRequest
) -> AsyncIterator[AsyncCloudFormationClient]:
    """A client in the test's mode, recorded or replayed per test function."""
    name = cast(pytest.Function, request.node).originalname
    path = Path(__file__).parent / "recordings" / name / "cloud_formation.py"
    async with AsyncExitStack() as stack:
        if mode == "async":
            client = AsyncCloudFormationClient(
                await AsyncCloudFormationConfig.resolve(region=REGION)
            )
            await stack.enter_async_context(client)
            await stack.enter_async_context(await instrument_async(client, path=path))
            yield client
        else:
            sync = CloudFormationClient(CloudFormationConfig.resolve(region=REGION))
            stack.enter_context(instrument(sync, path=path))
            adapter = await stack.enter_async_context(AwaitableClient(sync))
            yield cast(AsyncCloudFormationClient, adapter)


async def test_create_describe_delete_stack(
    cloudformation: AsyncCloudFormationClient,
) -> None:
    """A stack created with a parameter and tag reaches CREATE_COMPLETE with its outputs, then deletes."""
    prefix = "aws-sdk-python-recorded-lifecycle"
    created = await cloudformation.create_stack(
        stack_name=f"{prefix}-{uuid4().hex[:8]}",
        template_body=QUEUE_TEMPLATE,
        parameters=[{"parameter_key": "Delay", "parameter_value": "1"}],
        tags=[{"key": "Purpose", "value": "RecordedTest"}],
    )
    assert created.stack_id

    stack = await _wait_for_status(cloudformation, created.stack_id, "CREATE_COMPLETE")
    assert (stack.stack_name or "").startswith(prefix)
    assert stack.stack_id == created.stack_id
    assert [(p.parameter_key, p.parameter_value) for p in stack.parameters or []] == [
        ("Delay", "1")
    ]
    assert [(t.key, t.value) for t in stack.tags or []] == [("Purpose", "RecordedTest")]
    outputs = {o.output_key: o.output_value for o in stack.outputs or []}
    assert (outputs["QueueUrl"] or "").startswith("https://sqs.")

    await cloudformation.delete_stack(stack_name=created.stack_id)
    # Deleted stacks stay describable by ID only.
    deleted = await _wait_for_status(
        cloudformation, created.stack_id, "DELETE_COMPLETE"
    )
    assert deleted.deletion_time is not None


async def test_failed_create_rolls_back_with_reason(
    cloudformation: AsyncCloudFormationClient,
) -> None:
    """A stack whose resource fails to create rolls back and records the failure in its events."""
    created = await cloudformation.create_stack(
        stack_name=f"aws-sdk-python-recorded-rollback-{uuid4().hex[:8]}",
        template_body=FAILING_TEMPLATE,
    )
    assert created.stack_id
    try:
        await _wait_for_status(cloudformation, created.stack_id, "ROLLBACK_COMPLETE")

        events = await cloudformation.describe_stack_events(stack_name=created.stack_id)
        failures = [
            e
            for e in events.stack_events or []
            if e.resource_status == "CREATE_FAILED" and e.logical_resource_id == "Queue"
        ]
        assert failures
        assert failures[0].resource_status_reason
    finally:
        await cloudformation.delete_stack(stack_name=created.stack_id)
        await _wait_for_status(cloudformation, created.stack_id, "DELETE_COMPLETE")


async def test_validate_template_reports_parameters_and_description(
    cloudformation: AsyncCloudFormationClient,
) -> None:
    """ValidateTemplate returns the template's description and parameter declarations."""
    result = await cloudformation.validate_template(template_body=QUEUE_TEMPLATE)
    assert result.description == "aws-sdk-python recorded test"
    assert [(p.parameter_key, p.default_value) for p in result.parameters or []] == [
        ("Delay", "0")
    ]


async def _wait_for_status(
    client: AsyncCloudFormationClient, stack_id: str, target: str
) -> Stack:
    """Wait for the stack to reach ``target``, failing at once on any other settled status."""

    async def describe() -> Stack:
        output = await client.describe_stacks(stack_name=stack_id)
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

    return await wait_until(
        describe, reached_target, interval=POLL_INTERVAL, timeout=600
    )
