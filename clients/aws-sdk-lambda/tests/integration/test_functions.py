# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Read-only Lambda flows, adapted from JS v3 lambda-features.e2e.

Creating and invoking a function needs an execution role, which would pull the
IAM client into this package's test dependencies, so those flows are omitted.
"""

import pytest
from aws_sdk_lambda.aio.client import AsyncLambdaClient
from aws_sdk_lambda.models import (
    GetFunctionInput,
    ListFunctionsInput,
    ResourceNotFoundException,
)

from . import unique_name

MAX_PAGES = 3


async def test_list_functions_marker_pagination(
    lambda_client: AsyncLambdaClient,
) -> None:
    """Following next_marker with one item per page yields distinct functions."""
    names: list[str] = []
    marker: str | None = None
    for _ in range(MAX_PAGES):
        page = await lambda_client.list_functions(
            ListFunctionsInput(max_items=1, marker=marker)
        )
        functions = page.functions or []
        assert len(functions) <= 1
        names.extend(f.function_name for f in functions if f.function_name)
        marker = page.next_marker
        if marker is None:
            break

    if marker is None and len(names) < 2:
        pytest.skip("account has fewer than two functions to paginate over")
    assert len(names) == len(set(names))


async def test_get_missing_function_raises_modeled_error(
    lambda_client: AsyncLambdaClient,
) -> None:
    """GetFunction on an unknown name raises ResourceNotFoundException with a 404."""
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await lambda_client.get_function(GetFunctionInput(function_name=unique_name()))

    assert exc_info.value.response_metadata.http_status_code == 404
