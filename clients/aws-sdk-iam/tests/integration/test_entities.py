# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""User and role lifecycle, pagination and error shapes, from JS v3 IAM e2e."""

import json
from urllib.parse import unquote

import pytest
from aws_sdk_iam.aio.client import AsyncIAMClient
from aws_sdk_iam.models import (
    CreateRoleInput,
    CreateUserInput,
    DeleteRolePolicyInput,
    DeleteUserInput,
    EntityAlreadyExistsException,
    GetRoleInput,
    GetRolePolicyInput,
    GetUserInput,
    ListRolePoliciesInput,
    ListRoleTagsInput,
    ListUsersInput,
    ListUserTagsInput,
    NoSuchEntityException,
    PutRolePolicyInput,
    Tag,
    TagUserInput,
)
from waiters import wait_until, wait_until_gone

from . import INTEG_TAG, unique_name
from .conftest import Cleanup

TRUST_POLICY = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
)

INLINE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": "s3:ListAllMyBuckets", "Resource": "*"}
    ],
}


async def test_user_tags_and_deletion(iam: AsyncIAMClient, cleanup: Cleanup) -> None:
    """Verifies a user's creation tags and later tag additions are listed, and that a deleted user is NoSuchEntity."""
    name = unique_name("user-")
    created = await iam.create_user(CreateUserInput(user_name=name, tags=[INTEG_TAG]))
    cleanup.users.append(name)
    assert created.user is not None
    assert created.user.user_name == name
    await wait_until(
        lambda: iam.get_user(GetUserInput(user_name=name)),
        retry_on=(NoSuchEntityException,),
        interval=2,
    )

    await iam.tag_user(
        TagUserInput(user_name=name, tags=[Tag(key="Stage", value="two")])
    )
    tags = await wait_until(
        lambda: iam.list_user_tags(ListUserTagsInput(user_name=name)),
        lambda out: len(out.tags) == 2,
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    assert {t.key: t.value for t in tags.tags} == {
        "Purpose": "IntegTest",
        "Stage": "two",
    }

    await iam.delete_user(DeleteUserInput(user_name=name))
    cleanup.users.remove(name)
    await wait_until_gone(
        lambda: iam.get_user(GetUserInput(user_name=name)),
        gone_on=(NoSuchEntityException,),
        interval=2,
    )
    with pytest.raises(NoSuchEntityException) as caught:
        await iam.get_user(GetUserInput(user_name=name))
    assert caught.value.response_metadata.http_status_code == 404


async def test_role_inline_policy_lifecycle(
    iam: AsyncIAMClient, cleanup: Cleanup
) -> None:
    """Verifies a tagged role accepts, returns, lists and removes an inline policy."""
    role = unique_name("role-")
    policy = "inline"
    created = await iam.create_role(
        CreateRoleInput(
            role_name=role, assume_role_policy_document=TRUST_POLICY, tags=[INTEG_TAG]
        )
    )
    cleanup.roles.append(role)
    assert created.role.role_name == role
    assert created.role.arn.endswith(f":role/{role}")

    tags = await wait_until(
        lambda: iam.list_role_tags(ListRoleTagsInput(role_name=role)),
        lambda out: len(out.tags) == 1,
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    assert [(t.key, t.value) for t in tags.tags] == [("Purpose", "IntegTest")]

    await wait_until(
        lambda: iam.get_role(GetRoleInput(role_name=role)),
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    await iam.put_role_policy(
        PutRolePolicyInput(
            role_name=role,
            policy_name=policy,
            policy_document=json.dumps(INLINE_POLICY),
        )
    )
    listed = await wait_until(
        lambda: iam.list_role_policies(ListRolePoliciesInput(role_name=role)),
        lambda out: out.policy_names == [policy],
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    assert listed.policy_names == [policy]

    fetched = await wait_until(
        lambda: iam.get_role_policy(
            GetRolePolicyInput(role_name=role, policy_name=policy)
        ),
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    # IAM returns the document URL-encoded.
    assert json.loads(unquote(fetched.policy_document)) == INLINE_POLICY

    await iam.delete_role_policy(
        DeleteRolePolicyInput(role_name=role, policy_name=policy)
    )
    listed = await wait_until(
        lambda: iam.list_role_policies(ListRolePoliciesInput(role_name=role)),
        lambda out: out.policy_names == [],
        interval=2,
    )
    assert listed.policy_names == []

    role_info = await wait_until(
        lambda: iam.get_role(GetRoleInput(role_name=role)),
        retry_on=(NoSuchEntityException,),
        interval=2,
    )
    assert role_info.role.role_id == created.role.role_id


async def test_list_users_follows_marker_pages(
    iam: AsyncIAMClient, cleanup: Cleanup
) -> None:
    """Verifies ListUsers with MaxItems=1 pages through every user under a unique path."""
    path = f"/{unique_name('path-')}/"
    names = {unique_name(f"page{i}-") for i in range(3)}
    for name in names:
        await iam.create_user(CreateUserInput(user_name=name, path=path))
        cleanup.users.append(name)

    seen, pages = await wait_until(
        lambda: _list_users_one_per_page(iam, path),
        lambda result: set(result[0]) == names,
        interval=2,
    )

    assert pages == 3
    assert set(seen) == names
    assert len(seen) == len(names)


@pytest.mark.skip(
    reason="TODO: the query-protocol deserializer leaves EntityAlreadyExistsException.message empty"
)
async def test_duplicate_user_raises_entity_already_exists(
    iam: AsyncIAMClient, cleanup: Cleanup
) -> None:
    """Verifies creating an existing user raises the modeled EntityAlreadyExistsException."""
    name = unique_name("dupe-")
    await iam.create_user(CreateUserInput(user_name=name))
    cleanup.users.append(name)

    with pytest.raises(EntityAlreadyExistsException) as caught:
        await iam.create_user(CreateUserInput(user_name=name))

    error = caught.value
    assert error.fault == "client"
    assert error.message
    assert error.response_metadata.http_status_code == 409
    assert error.response_metadata.request_id


async def _list_users_one_per_page(
    iam: AsyncIAMClient, path: str
) -> tuple[list[str], int]:
    seen: list[str] = []
    pages = 0
    marker: str | None = None
    while True:
        page = await iam.list_users(
            ListUsersInput(path_prefix=path, max_items=1, marker=marker)
        )
        pages += 1
        seen.extend(user.user_name for user in page.users)
        if not page.is_truncated:
            return seen, pages
        marker = page.marker
        assert marker
