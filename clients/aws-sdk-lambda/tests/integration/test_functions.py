# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Read-only Lambda flows, adapted from JS v3 lambda-features.e2e.

Creating and invoking a function needs an execution role, which would pull the
IAM client into this package's test dependencies, so those flows are omitted.
"""

import pytest
from aws_sdk_lambda.aio.client import AsyncLambdaClient
from aws_sdk_lambda.models import GetFunctionInput, ResourceNotFoundException

from . import unique_name


async def test_get_missing_function_raises_modeled_error(
    lambda_client: AsyncLambdaClient,
) -> None:
    """GetFunction on an unknown name raises ResourceNotFoundException with a 404."""
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await lambda_client.get_function(GetFunctionInput(function_name=unique_name()))

    assert exc_info.value.response_metadata.http_status_code == 404
