# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the RDS integration tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_rds.aio.client import AsyncRDSClient
from aws_sdk_rds.models import (
    CreateDBParameterGroupInput,
    DBParameterGroup,
    DBParameterGroupNotFoundFault,
    DeleteDBParameterGroupInput,
    DescribeDBParameterGroupsInput,
    Tag,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until

from . import create_async_client, create_sync_client, unique_name

PARAMETER_GROUP_FAMILY = "mysql8.0"


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def rds(mode: Mode) -> AsyncIterator[AsyncRDSClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
async def parameter_group(rds: AsyncRDSClient) -> AsyncIterator[DBParameterGroup]:
    """A tagged DB parameter group, deleted after the test unless the test already did."""
    created = await rds.create_db_parameter_group(
        CreateDBParameterGroupInput(
            db_parameter_group_name=unique_name("pg-"),
            db_parameter_group_family=PARAMETER_GROUP_FAMILY,
            description="aws-sdk-python integration test",
            tags=[Tag(key="Purpose", value="IntegTest")],
        )
    )
    group = created.db_parameter_group
    assert group is not None
    assert group.db_parameter_group_name is not None
    try:
        await wait_until(
            lambda: rds.describe_db_parameter_groups(
                DescribeDBParameterGroupsInput(
                    db_parameter_group_name=group.db_parameter_group_name
                )
            ),
            retry_on=(DBParameterGroupNotFoundFault,),
            interval=2,
            timeout=60,
        )
        yield group
    finally:
        try:
            await rds.delete_db_parameter_group(
                DeleteDBParameterGroupInput(
                    db_parameter_group_name=group.db_parameter_group_name
                )
            )
        except DBParameterGroupNotFoundFault:
            pass
