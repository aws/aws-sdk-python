# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the EC2 integration tests."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_ec2.aio.client import AsyncEC2Client
from aws_sdk_ec2.models import (
    CreateSecurityGroupInput,
    DeleteSecurityGroupInput,
    DescribeSecurityGroupsInput,
    DescribeVpcsInput,
    Filter,
    ResourceType,
    TagSpecification,
)
from dual_mode import MODES, Mode, open_client
from waiters import wait_until

from . import (
    EVENTUAL_ERRORS,
    PURPOSE_TAG,
    create_async_client,
    create_sync_client,
    unique_name,
)


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def ec2(mode: Mode) -> AsyncIterator[AsyncEC2Client]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
async def default_vpc_id(ec2: AsyncEC2Client) -> str:
    vpcs = await ec2.describe_vpcs(
        DescribeVpcsInput(filters=[Filter(name="is-default", values=["true"])])
    )
    ids = [v.vpc_id for v in vpcs.vpcs or [] if v.vpc_id is not None]
    if not ids:
        pytest.skip("account has no default VPC in the test region")
    return ids[0]


@pytest.fixture
async def security_group(
    ec2: AsyncEC2Client, default_vpc_id: str
) -> AsyncIterator[str]:
    """The ID of a tagged security group in the default VPC, deleted after the test."""
    created = await ec2.create_security_group(
        CreateSecurityGroupInput(
            group_name=unique_name("sg-"),
            description="aws-sdk-python integration test",
            vpc_id=default_vpc_id,
            tag_specifications=[
                TagSpecification(
                    resource_type=ResourceType.SECURITY_GROUP, tags=[PURPOSE_TAG]
                )
            ],
        )
    )
    group_id = created.group_id
    assert group_id is not None
    try:
        await wait_until(
            lambda: ec2.describe_security_groups(
                DescribeSecurityGroupsInput(group_ids=[group_id])
            ),
            lambda found: bool(found.security_groups),
            retry_on=EVENTUAL_ERRORS,
            interval=2,
            timeout=60,
        )
        yield group_id
    finally:
        # Network interfaces and rules can briefly keep the group in use.
        await wait_until(
            lambda: ec2.delete_security_group(
                DeleteSecurityGroupInput(group_id=group_id)
            ),
            retry_on=EVENTUAL_ERRORS,
            interval=2,
            timeout=60,
        )
