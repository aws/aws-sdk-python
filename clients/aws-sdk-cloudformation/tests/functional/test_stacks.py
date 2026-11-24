# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stack lifecycle, rollback and validation against mocked CloudFormation responses.

Each test checks the AWS Query request the client sends and the model it parses from
the service's XML, including the polling loop a caller runs while a stack settles.
"""

from aws_sdk_cloudformation.models import (
    CreateStackInput,
    DeleteStackInput,
    DescribeStackEventsInput,
    Parameter,
    StackStatus,
    Tag,
    ValidateTemplateInput,
)

from . import (
    FAILING_TEMPLATE,
    HOSTNAME,
    QUEUE_TEMPLATE,
    VALIDATE_TEMPLATE_RESPONSE,
    XML_HEADERS,
    MockedClient,
    create_stack_response,
    delete_stack_response,
    describe_stack_events_response,
    describe_stacks_response,
    form,
    stack_id,
    wait_for_stack_status,
)

STACK_NAME = "aws-sdk-python-functional-stack"


async def test_create_describe_delete_stack(cloudformation: MockedClient) -> None:
    """A stack created with a parameter and tag reaches CREATE_COMPLETE with its outputs, then deletes."""
    client, http = cloudformation
    arn = stack_id(STACK_NAME)

    http.expect_request(
        method="POST",
        hostname=HOSTNAME,
        path="/",
        headers={"content-type": "application/x-www-form-urlencoded"},
        body=form(
            {
                "Action": "CreateStack",
                "Version": "2010-05-15",
                "StackName": STACK_NAME,
                "TemplateBody": QUEUE_TEMPLATE,
                "Parameters.member.1.ParameterKey": "Delay",
                "Parameters.member.1.ParameterValue": "1",
                "Tags.member.1.Key": "Purpose",
                "Tags.member.1.Value": "IntegTest",
            }
        ),
    ).respond_with(headers=XML_HEADERS, body=create_stack_response(STACK_NAME))
    # The stack is still being created on the first poll.
    http.expect_request(
        body=form({"Action": "DescribeStacks", "StackName": arn})
    ).times(2).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME, "CREATE_IN_PROGRESS", reason="User Initiated"
        ),
    ).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(STACK_NAME, "CREATE_COMPLETE", outputs=True),
    )
    http.expect_request(
        body=form({"Action": "DeleteStack", "StackName": arn})
    ).respond_with(headers=XML_HEADERS, body=delete_stack_response())
    http.expect_request(
        body=form({"Action": "DescribeStacks", "StackName": arn})
    ).times(2).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME, "DELETE_IN_PROGRESS", reason="User Initiated", outputs=True
        ),
    ).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME, "DELETE_COMPLETE", deleted=True, outputs=True
        ),
    )

    created = await client.create_stack(
        CreateStackInput(
            stack_name=STACK_NAME,
            template_body=QUEUE_TEMPLATE,
            parameters=[Parameter(parameter_key="Delay", parameter_value="1")],
            tags=[Tag(key="Purpose", value="IntegTest")],
        )
    )
    assert created.stack_id == arn

    stack = await wait_for_stack_status(client, arn, StackStatus.CREATE_COMPLETE)
    assert stack.stack_name == STACK_NAME
    assert stack.stack_id == arn
    assert [(p.parameter_key, p.parameter_value) for p in stack.parameters or []] == [
        ("Delay", "1")
    ]
    assert [(t.key, t.value) for t in stack.tags or []] == [("Purpose", "IntegTest")]
    outputs = {o.output_key: o.output_value for o in stack.outputs or []}
    assert (outputs["QueueUrl"] or "").startswith("https://sqs.")
    assert stack.deletion_time is None

    await client.delete_stack(DeleteStackInput(stack_name=arn))
    # Deleted stacks stay describable by ID only.
    deleted = await wait_for_stack_status(client, arn, StackStatus.DELETE_COMPLETE)
    assert deleted.deletion_time is not None

    assert len(http.requests) == 6


async def test_failed_create_rolls_back_with_reason(
    cloudformation: MockedClient,
) -> None:
    """A stack whose resource fails to create rolls back and records the failure in its events."""
    client, http = cloudformation
    arn = stack_id(STACK_NAME)

    http.expect_request(
        body=form(
            {
                "Action": "CreateStack",
                "StackName": STACK_NAME,
                "TemplateBody": FAILING_TEMPLATE,
            }
        )
    ).respond_with(headers=XML_HEADERS, body=create_stack_response(STACK_NAME))
    # Every *_IN_PROGRESS status keeps the caller polling; only a settled one ends it.
    http.expect_request(
        body=form({"Action": "DescribeStacks", "StackName": arn})
    ).times(3).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME, "CREATE_IN_PROGRESS", parameters=False, tags=False
        ),
    ).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME,
            "ROLLBACK_IN_PROGRESS",
            reason="The following resource(s) failed to create: [Queue].",
            parameters=False,
            tags=False,
        ),
    ).respond_with(
        headers=XML_HEADERS,
        body=describe_stacks_response(
            STACK_NAME, "ROLLBACK_COMPLETE", deleted=True, parameters=False, tags=False
        ),
    )
    http.expect_request(
        body=form({"Action": "DescribeStackEvents", "StackName": arn})
    ).respond_with(headers=XML_HEADERS, body=describe_stack_events_response(STACK_NAME))

    created = await client.create_stack(
        CreateStackInput(stack_name=STACK_NAME, template_body=FAILING_TEMPLATE)
    )
    assert created.stack_id == arn

    rolled_back = await wait_for_stack_status(
        client, arn, StackStatus.ROLLBACK_COMPLETE
    )
    assert rolled_back.tags == []

    events = await client.describe_stack_events(
        DescribeStackEventsInput(stack_name=arn)
    )
    assert len(events.stack_events or []) == 6
    failures = [
        e
        for e in events.stack_events or []
        if e.resource_status == StackStatus.CREATE_FAILED
        and e.logical_resource_id == "Queue"
    ]
    assert len(failures) == 1
    assert failures[0].resource_type == "AWS::SQS::Queue"
    assert failures[0].resource_status_reason
    assert (
        "Can only include alphanumeric characters" in failures[0].resource_status_reason
    )

    assert len(http.requests) == 5


async def test_validate_template_reports_parameters_and_description(
    cloudformation: MockedClient,
) -> None:
    """ValidateTemplate returns the template's description and parameter declarations."""
    client, http = cloudformation

    http.expect_request(
        method="POST",
        hostname=HOSTNAME,
        body=form({"Action": "ValidateTemplate", "TemplateBody": QUEUE_TEMPLATE}),
    ).respond_with(headers=XML_HEADERS, body=VALIDATE_TEMPLATE_RESPONSE)

    result = await client.validate_template(
        ValidateTemplateInput(template_body=QUEUE_TEMPLATE)
    )

    assert result.description == "aws-sdk-python integration test"
    assert [
        (p.parameter_key, p.default_value, p.no_echo) for p in result.parameters or []
    ] == [("Delay", "0", False)]
