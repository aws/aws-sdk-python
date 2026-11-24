# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""CloudFormation tests against mocked HTTP, written once and run in both sync and async modes.

The response bodies are trimmed copies of what the live service returned to the
integration tests these replace, so the parsing they exercise is the real shape.
"""

import json
from collections.abc import Callable, Mapping
from typing import NamedTuple
from urllib.parse import parse_qs

from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.models import DescribeStacksInput, Stack
from smithy_test import HTTPMockController
from waiters import wait_until

REGION = "us-west-2"
HOSTNAME = f"cloudformation.{REGION}.amazonaws.com"
ACCOUNT = "123456789012"

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


class MockedClient(NamedTuple):
    """A client in the test's mode and the controller answering its requests."""

    client: AsyncCloudFormationClient
    http: HTTPMockController


def stack_id(name: str) -> str:
    return f"arn:aws:cloudformation:{REGION}:{ACCOUNT}:stack/{name}/7f8f0cd0-e838-11f1-b256-06ffd18d37d9"


def form(expected: Mapping[str, str]) -> Callable[[bytes], None]:
    """Match an AWS Query request body containing every expected field."""

    def check(body: bytes) -> None:
        actual = {
            key: values[0]
            for key, values in parse_qs(body.decode(), keep_blank_values=True).items()
        }
        for key, value in expected.items():
            assert actual.get(key) == value, (
                f"{key}: expected {value!r}, got {actual.get(key)!r}"
            )

    return check


XML_HEADERS = {"content-type": "text/xml"}
_NS = 'xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/"'
_REQUEST_ID = "<ResponseMetadata><RequestId>16b6fc9d-9b25-4459-a779-a8a557f32a18</RequestId></ResponseMetadata>"


def create_stack_response(name: str) -> str:
    return f"""<CreateStackResponse {_NS}>
  <CreateStackResult>
    <StackId>{stack_id(name)}</StackId>
    <OperationId>7f906c60-e838-11f1-b256-06ffd18d37d9</OperationId>
  </CreateStackResult>
  {_REQUEST_ID}
</CreateStackResponse>"""


def delete_stack_response() -> str:
    return f"<DeleteStackResponse {_NS}>{_REQUEST_ID}</DeleteStackResponse>"


def describe_stacks_response(
    name: str,
    status: str,
    *,
    reason: str | None = None,
    deleted: bool = False,
    outputs: bool = False,
    parameters: bool = True,
    tags: bool = True,
) -> str:
    """One stack as DescribeStacks returns it after CreateStack with QUEUE_TEMPLATE."""
    queue_url = (
        f"https://sqs.{REGION}.amazonaws.com/{ACCOUNT}/{name}-Queue-RtYxdWA2JABP"
    )
    optional = [
        f"<Outputs><member><OutputKey>QueueUrl</OutputKey><OutputValue>{queue_url}</OutputValue></member></Outputs>"
        if outputs
        else "",
        "<DeletionTime>2026-11-24T18:55:46.664Z</DeletionTime>" if deleted else "",
        f"<StackStatusReason>{reason}</StackStatusReason>" if reason else "",
        "<Parameters><member><ParameterKey>Delay</ParameterKey><ParameterValue>1</ParameterValue></member></Parameters>"
        if parameters
        else "",
        "<Tags><member><Value>IntegTest</Value><Key>Purpose</Key></member></Tags>"
        if tags
        else "<Tags/>",
    ]
    return f"""<DescribeStacksResponse {_NS}>
  <DescribeStacksResult>
    <Stacks>
      <member>
        <CreationTime>2026-11-24T18:54:38.138Z</CreationTime>
        <NotificationARNs/>
        <StackName>{name}</StackName>
        <Description>aws-sdk-python integration test</Description>
        <RollbackConfiguration/>
        <DriftInformation><StackDriftStatus>NOT_CHECKED</StackDriftStatus></DriftInformation>
        <EnableTerminationProtection>false</EnableTerminationProtection>
        <StackId>{stack_id(name)}</StackId>
        <StackStatus>{status}</StackStatus>
        <DisableRollback>false</DisableRollback>
        {"".join(optional)}
      </member>
    </Stacks>
  </DescribeStacksResult>
  {_REQUEST_ID}
</DescribeStacksResponse>"""


CREATE_FAILED_REASON = (
    "Resource handler returned message: &quot;Can only include alphanumeric "
    "characters, hyphens, or underscores. 1 to 80 in length (Service: Sqs, "
    "Status Code: 400, Request ID: 3e0f8be7-6bd2-5003-a242-e8988be4fdca) "
    "(SDK Attempt Count: 1)&quot; (RequestToken: "
    "d17389e5-90af-32ca-62f3-cc3adfd46f05, HandlerErrorCode: GeneralServiceException)"
)


def describe_stack_events_response(name: str) -> str:
    """The events of a stack whose Queue failed to create and was rolled back, newest first."""
    arn = stack_id(name)

    def event(
        event_id: str,
        logical_id: str,
        status: str,
        resource_type: str,
        reason: str = "",
    ) -> str:
        reason_xml = (
            f"<ResourceStatusReason>{reason}</ResourceStatusReason>" if reason else ""
        )
        return f"""      <member>
        <EventId>{event_id}</EventId>
        <StackId>{arn}</StackId>
        <StackName>{name}</StackName>
        <LogicalResourceId>{logical_id}</LogicalResourceId>
        <ResourceStatus>{status}</ResourceStatus>{reason_xml}
        <Timestamp>2026-11-24T18:56:55.061Z</Timestamp>
        <ResourceType>{resource_type}</ResourceType>
      </member>"""

    stack = "AWS::CloudFormation::Stack"
    queue = "AWS::SQS::Queue"
    return f"""<DescribeStackEventsResponse {_NS}>
  <DescribeStackEventsResult>
    <StackEvents>
{event("1f0d47e0-e839-11f1-9538-023c48e39cad", name, "ROLLBACK_COMPLETE", stack)}
{event("Queue-DELETE_COMPLETE", "Queue", "DELETE_COMPLETE", queue)}
{
        event(
            "d165ac30-e838-11f1-8b9b-02ffe5e4c45b",
            name,
            "ROLLBACK_IN_PROGRESS",
            stack,
            "The following resource(s) failed to create: [Queue]. Rollback requested by user.",
        )
    }
{event("Queue-CREATE_FAILED", "Queue", "CREATE_FAILED", queue, CREATE_FAILED_REASON)}
{event("Queue-CREATE_IN_PROGRESS", "Queue", "CREATE_IN_PROGRESS", queue)}
{
        event(
            "cf5569d0-e838-11f1-9f93-02b9c6c9d397",
            name,
            "CREATE_IN_PROGRESS",
            stack,
            "User Initiated",
        )
    }
    </StackEvents>
  </DescribeStackEventsResult>
  {_REQUEST_ID}
</DescribeStackEventsResponse>"""


VALIDATE_TEMPLATE_RESPONSE = f"""<ValidateTemplateResponse {_NS}>
  <ValidateTemplateResult>
    <Description>aws-sdk-python integration test</Description>
    <Parameters>
      <member>
        <NoEcho>false</NoEcho>
        <DefaultValue>0</DefaultValue>
        <ParameterKey>Delay</ParameterKey>
      </member>
    </Parameters>
  </ValidateTemplateResult>
  {_REQUEST_ID}
</ValidateTemplateResponse>"""


async def wait_for_stack_status(
    client: AsyncCloudFormationClient, arn: str, target: str
) -> Stack:
    """Poll DescribeStacks until ``target``, failing at once on any other settled status.

    The same loop as the live tests use, without the delay between polls: the mock
    answers each poll from its queue of responses.
    """

    async def describe() -> Stack:
        output = await client.describe_stacks(DescribeStacksInput(stack_name=arn))
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

    return await wait_until(describe, reached_target, interval=0, timeout=5)
