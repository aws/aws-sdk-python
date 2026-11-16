# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Fixtures for the Cognito Identity integration tests."""

from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack
from typing import cast

import pytest
from aws_sdk_cognito_identity.aio.client import AsyncCognitoIdentityClient
from aws_sdk_cognito_identity.models import (
    CreateIdentityPoolInput,
    DeleteIdentityPoolInput,
)
from dual_mode import MODES, Mode, open_client

from . import create_async_client, create_sync_client, unique_name


@pytest.fixture(params=MODES)
def mode(request: pytest.FixtureRequest) -> Mode:
    return cast(Mode, request.param)


@pytest.fixture
async def cognito(mode: Mode) -> AsyncIterator[AsyncCognitoIdentityClient]:
    async with AsyncExitStack() as stack:
        yield await open_client(stack, mode, create_async_client, create_sync_client)


@pytest.fixture
def identity_pool_id() -> Iterator[str]:
    """An identity pool allowing unauthenticated identities, deleted after the test."""
    with create_sync_client() as client:
        pool = client.create_identity_pool(
            CreateIdentityPoolInput(
                identity_pool_name=unique_name(),
                allow_unauthenticated_identities=True,
                identity_pool_tags={"Purpose": "IntegTest"},
            )
        )
        try:
            yield pool.identity_pool_id
        finally:
            client.delete_identity_pool(
                DeleteIdentityPoolInput(identity_pool_id=pool.identity_pool_id)
            )
