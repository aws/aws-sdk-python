# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Q Business integration tests.

Creates and tears down a Q Business application (with an index and retriever)
once per test session. The ``qbusiness_app`` fixture provides the application
ID.
"""

import asyncio
import uuid

import pytest

from aws_sdk_qbusiness.models import (
    ApplicationStatus,
    IndexStatus,
    NativeIndexConfiguration,
    RetrieverConfigurationNativeIndexConfiguration,
    RetrieverStatus,
    RetrieverType,
    Tag,
    ThrottlingException,
)

from . import REGION, create_qbusiness_client

# Tags applied to all resources so orphaned resources from interrupted
# test runs can be discovered and cleaned up.
_TAGS = [Tag(key="Purpose", value="IntegTest")]

_POLL_INTERVAL_SECONDS = 10
_POLL_TIMEOUT_SECONDS = 300

# ThrottlingException is not marked retryable in the service model, so the SDK
# does not retry it automatically. Used for CreateApplication under concurrency.
_THROTTLE_RETRY_DELAY_SECONDS = 5
_THROTTLE_RETRY_TIMEOUT_SECONDS = 300


async def _wait_for_application_active(client, application_id: str) -> None:
    """Wait for an Application to reach ACTIVE status.

    Args:
        client: A Q Business client.
        application_id: The Application ID to poll.
    """
    deadline = asyncio.get_running_loop().time() + _POLL_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get_application(application_id=application_id)
        if response.status == ApplicationStatus.ACTIVE:
            return
        if response.status in {ApplicationStatus.FAILED, ApplicationStatus.DELETING}:
            raise RuntimeError(
                f"Application {application_id} entered terminal state {response.status}"
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Application {application_id} did not become ACTIVE in time")


async def _wait_for_index_active(client, application_id: str, index_id: str) -> None:
    """Wait for an Index to reach ACTIVE status.

    Args:
        client: A Q Business client.
        application_id: The parent Application ID.
        index_id: The Index ID to poll.
    """
    deadline = asyncio.get_running_loop().time() + _POLL_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get_index(
            application_id=application_id, index_id=index_id
        )
        if response.status == IndexStatus.ACTIVE:
            return
        if response.status in {IndexStatus.FAILED, IndexStatus.DELETING}:
            raise RuntimeError(
                f"Index {index_id} entered terminal state {response.status}"
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Index {index_id} did not become ACTIVE in time")


async def _wait_for_retriever_active(
    client, application_id: str, retriever_id: str
) -> None:
    """Wait for a Retriever to reach ACTIVE status.

    Args:
        client: A Q Business client.
        application_id: The parent Application ID.
        retriever_id: The Retriever ID to poll.
    """
    deadline = asyncio.get_running_loop().time() + _POLL_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get_retriever(
            application_id=application_id, retriever_id=retriever_id
        )
        if response.status == RetrieverStatus.ACTIVE:
            return
        if response.status == RetrieverStatus.FAILED:
            raise RuntimeError(
                f"Retriever {retriever_id} entered terminal state {response.status}"
            )
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Retriever {retriever_id} did not become ACTIVE in time")


async def _create_qbusiness_app(
    client, app_name: str, index_name: str, retriever_name: str
) -> str:
    """Create a Q Business application with index and retriever.

    Args:
        client: A Q Business client.
        app_name: The display name of the Application to create.
        index_name: The display name of the Index to create.
        retriever_name: The display name of the Retriever to create.

    Returns:
        The application ID.
    """
    # ThrottlingException is not marked retryable in the service model, so the
    # SDK does not retry it automatically. Retry here for concurrent test runs.
    deadline = asyncio.get_running_loop().time() + _THROTTLE_RETRY_TIMEOUT_SECONDS
    while True:
        try:
            response = await client.create_application(
                display_name=app_name,
                identity_type="ANONYMOUS",
                tags=_TAGS,
                client_token=str(uuid.uuid4()),
            )
            break
        except ThrottlingException:
            if asyncio.get_running_loop().time() >= deadline:
                raise
            await asyncio.sleep(_THROTTLE_RETRY_DELAY_SECONDS)
    application_id = response.application_id
    assert application_id is not None
    await _wait_for_application_active(client, application_id)

    response = await client.create_index(
        application_id=application_id,
        display_name=index_name,
        tags=_TAGS,
        client_token=str(uuid.uuid4()),
    )
    index_id = response.index_id
    assert index_id is not None
    await _wait_for_index_active(client, application_id, index_id)

    response = await client.create_retriever(
        application_id=application_id,
        display_name=retriever_name,
        type=RetrieverType.NATIVE_INDEX,
        configuration=RetrieverConfigurationNativeIndexConfiguration(
            value=NativeIndexConfiguration(index_id=index_id)
        ),
        tags=_TAGS,
        client_token=str(uuid.uuid4()),
    )
    retriever_id = response.retriever_id
    assert retriever_id is not None
    await _wait_for_retriever_active(client, application_id, retriever_id)

    return application_id


async def _delete_qbusiness_app(client, application_id: str | None) -> None:
    """Delete a Q Business application. Cascades to its index and retriever.

    Args:
        client: A Q Business client.
        application_id: The Application ID to delete, or None if creation failed.
    """
    if not application_id:
        return
    await client.delete_application(application_id=application_id)


@pytest.fixture(scope="session")
async def qbusiness_app():
    """Create a Q Business application for the test session and delete it after."""
    unique_suffix = uuid.uuid4().hex[:16]
    app_name = f"integ-test-qbusiness-app-{unique_suffix}"
    index_name = f"integ-test-qbusiness-index-{unique_suffix}"
    retriever_name = f"integ-test-qbusiness-retriever-{unique_suffix}"

    async with await create_qbusiness_client(REGION) as client:
        application_id: str | None = None
        try:
            application_id = await _create_qbusiness_app(
                client, app_name, index_name, retriever_name
            )
            yield application_id
        finally:
            await _delete_qbusiness_app(client, application_id)
