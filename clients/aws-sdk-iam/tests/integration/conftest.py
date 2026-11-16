# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the IAM integration tests."""

from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import cast

import pytest
from aws_sdk_iam.aio.client import AsyncIAMClient
from aws_sdk_iam.client import IAMClient
from aws_sdk_iam.models import (
    DeleteRoleInput,
    DeleteRolePolicyInput,
    DeleteUserInput,
    ListRolePoliciesInput,
)
from dual_mode import MODES, Mode, open_client

from . import create_async_client, create_sync_client


@dataclass
class Cleanup:
    """Names of the users and roles a test created, removed at teardown."""

    users: list[str] = field(default_factory=lambda: [])
    roles: list[str] = field(default_factory=lambda: [])


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def iam(mode: Mode) -> AsyncIterator[AsyncIAMClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def cleanup() -> Iterator[Cleanup]:
    """Deletes every registered user and role, using the sync client so teardown needs no event loop."""
    created = Cleanup()
    try:
        yield created
    finally:
        with create_sync_client() as client:
            for user in created.users:
                client.delete_user(DeleteUserInput(user_name=user))
            for role in created.roles:
                _delete_role(client, role)


def _delete_role(client: IAMClient, role: str) -> None:
    # A role with inline policies cannot be deleted.
    policies = client.list_role_policies(ListRolePoliciesInput(role_name=role))
    for policy in policies.policy_names:
        client.delete_role_policy(
            DeleteRolePolicyInput(role_name=role, policy_name=policy)
        )
    client.delete_role(DeleteRoleInput(role_name=role))
