# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Identity pool lifecycle, adapted from JS v3 cognito-identity e2e."""

import pytest
from aws_sdk_cognito_identity.aio.client import AsyncCognitoIdentityClient
from aws_sdk_cognito_identity.models import (
    CreateIdentityPoolInput,
    DeleteIdentityPoolInput,
    DescribeIdentityInput,
    DescribeIdentityPoolInput,
    GetIdInput,
    ListIdentitiesInput,
    ResourceNotFoundException,
)
from waiters import wait_until, wait_until_gone

from . import unique_name


async def test_create_describe_delete_pool(cognito: AsyncCognitoIdentityClient) -> None:
    """A pool round-trips its name, unauthenticated flag and tags, and is gone after delete."""
    name = unique_name()
    created = await cognito.create_identity_pool(
        CreateIdentityPoolInput(
            identity_pool_name=name,
            allow_unauthenticated_identities=True,
            identity_pool_tags={"Purpose": "IntegTest"},
        )
    )
    try:
        described = await wait_until(
            lambda: cognito.describe_identity_pool(
                DescribeIdentityPoolInput(identity_pool_id=created.identity_pool_id)
            ),
            retry_on=(ResourceNotFoundException,),
            interval=2,
        )
        assert described.identity_pool_name == name
        assert described.allow_unauthenticated_identities is True
        assert described.identity_pool_tags == {"Purpose": "IntegTest"}
    finally:
        await cognito.delete_identity_pool(
            DeleteIdentityPoolInput(identity_pool_id=created.identity_pool_id)
        )

    await wait_until_gone(
        lambda: cognito.describe_identity_pool(
            DescribeIdentityPoolInput(identity_pool_id=created.identity_pool_id)
        ),
        gone_on=(ResourceNotFoundException,),
        interval=2,
    )
    with pytest.raises(ResourceNotFoundException):
        await cognito.describe_identity_pool(
            DescribeIdentityPoolInput(identity_pool_id=created.identity_pool_id)
        )


async def test_unauthenticated_identity_is_created_and_listed(
    cognito: AsyncCognitoIdentityClient, identity_pool_id: str
) -> None:
    """GetId mints a stable unauthenticated identity that DescribeIdentity and ListIdentities return."""
    first = await cognito.get_id(GetIdInput(identity_pool_id=identity_pool_id))
    assert first.identity_id is not None
    assert first.identity_id.startswith("us-west-2:")

    identity_id = first.identity_id
    described = await wait_until(
        lambda: cognito.describe_identity(
            DescribeIdentityInput(identity_id=identity_id)
        ),
        retry_on=(ResourceNotFoundException,),
        interval=2,
    )
    assert described.identity_id == first.identity_id

    listed = await wait_until(
        lambda: cognito.list_identities(
            ListIdentitiesInput(identity_pool_id=identity_pool_id, max_results=10)
        ),
        lambda out: identity_id in [i.identity_id for i in out.identities or []],
        interval=2,
    )
    assert first.identity_id in [i.identity_id for i in listed.identities or []]
