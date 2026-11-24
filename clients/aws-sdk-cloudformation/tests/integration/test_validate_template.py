# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""One live round trip, so the Query protocol and signing are checked against the service."""

from aws_sdk_cloudformation.aio.client import AsyncCloudFormationClient
from aws_sdk_cloudformation.models import ValidateTemplateInput

from . import QUEUE_TEMPLATE


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
