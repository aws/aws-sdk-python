# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stack lifecycle, validation and pagination, from JS v3 cloudformation-features.e2e."""

from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.models import (
    CreateStackInput,
    DeleteStackInput,
    DescribeStackEventsInput,
    ListStacksInput,
    Parameter,
    StackStatus,
    Tag,
    ValidateTemplateInput,
)

from . import FAILING_TEMPLATE, QUEUE_TEMPLATE, unique_stack_name, wait_for_stack_status


async def test_create_describe_delete_stack(
    cloudformation: AsyncCloudFormationClient, created_stacks: list[str]
) -> None:
    """A stack created with a parameter and tag reaches CREATE_COMPLETE with its outputs, then deletes."""
    name = unique_stack_name()
    created = await cloudformation.create_stack(
        CreateStackInput(
            stack_name=name,
            template_body=QUEUE_TEMPLATE,
            parameters=[Parameter(parameter_key="Delay", parameter_value="1")],
            tags=[Tag(key="Purpose", value="IntegTest")],
        )
    )
    assert created.stack_id is not None
    created_stacks.append(created.stack_id)

    stack = await wait_for_stack_status(
        cloudformation, created.stack_id, StackStatus.CREATE_COMPLETE
    )
    assert stack.stack_name == name
    assert stack.stack_id == created.stack_id
    assert [(p.parameter_key, p.parameter_value) for p in stack.parameters or []] == [
        ("Delay", "1")
    ]
    assert [(t.key, t.value) for t in stack.tags or []] == [("Purpose", "IntegTest")]
    outputs = {o.output_key: o.output_value for o in stack.outputs or []}
    assert (outputs["QueueUrl"] or "").startswith("https://sqs.")

    await cloudformation.delete_stack(DeleteStackInput(stack_name=created.stack_id))
    # Deleted stacks stay describable by ID only.
    deleted = await wait_for_stack_status(
        cloudformation, created.stack_id, StackStatus.DELETE_COMPLETE
    )
    assert deleted.deletion_time is not None


async def test_failed_create_rolls_back_with_reason(
    cloudformation: AsyncCloudFormationClient, created_stacks: list[str]
) -> None:
    """A stack whose resource fails to create rolls back and records the failure in its events."""
    created = await cloudformation.create_stack(
        CreateStackInput(stack_name=unique_stack_name(), template_body=FAILING_TEMPLATE)
    )
    assert created.stack_id is not None
    created_stacks.append(created.stack_id)

    await wait_for_stack_status(
        cloudformation, created.stack_id, StackStatus.ROLLBACK_COMPLETE
    )

    events = await cloudformation.describe_stack_events(
        DescribeStackEventsInput(stack_name=created.stack_id)
    )
    failures = [
        e
        for e in events.stack_events or []
        if e.resource_status == StackStatus.CREATE_FAILED
        and e.logical_resource_id == "Queue"
    ]
    assert failures
    assert failures[0].resource_status_reason


async def test_validate_template_reports_parameters_and_description(
    cloudformation: AsyncCloudFormationClient,
) -> None:
    """ValidateTemplate returns the template's description and parameter declarations."""
    result = await cloudformation.validate_template(
        ValidateTemplateInput(template_body=QUEUE_TEMPLATE)
    )
    assert result.description == "aws-sdk-python integration test"
    assert [(p.parameter_key, p.default_value) for p in result.parameters or []] == [
        ("Delay", "0")
    ]


async def test_list_stacks_pages_to_the_end(
    cloudformation: AsyncCloudFormationClient,
) -> None:
    """Following next_token through ListStacks ends on a page without a token."""
    pages = 0
    token: str | None = None
    while True:
        page = await cloudformation.list_stacks(ListStacksInput(next_token=token))
        pages += 1
        assert pages < 1000
        token = page.next_token
        if token is None:
            break
    assert pages >= 1
