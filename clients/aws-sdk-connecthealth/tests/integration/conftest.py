# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for ConnectHealth integration tests.

Creates and tears down a ConnectHealth Domain with an ACTIVE Subscription
plus an S3 bucket once per test session. The ``connecthealth_resources``
fixture provides ``(domain_id, subscription_id, output_s3_uri)``.
"""

import asyncio
import uuid
from typing import Any

import boto3
import pytest

from aws_sdk_connecthealth.client import AsyncConnectHealthClient
from aws_sdk_connecthealth.models import SubscriptionStatus

from . import REGION, create_connecthealth_client

# Tags applied to all resources so orphaned resources from interrupted
# test runs can be discovered and cleaned up.
_TAGS = {"Purpose": "IntegTest"}

_SUBSCRIPTION_POLL_INTERVAL_SECONDS = 5
_SUBSCRIPTION_POLL_TIMEOUT_SECONDS = 300


async def _wait_for_subscription_inactive(
    client: AsyncConnectHealthClient, domain_id: str, subscription_id: str
) -> None:
    """Wait for a Subscription to report INACTIVE.

    DeleteDomain rejects a Domain whose Subscription is not yet deactivated.

    Args:
        client: A ConnectHealth client.
        domain_id: The parent Domain ID.
        subscription_id: The Subscription ID to poll.
    """
    deadline = asyncio.get_running_loop().time() + _SUBSCRIPTION_POLL_TIMEOUT_SECONDS
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get_subscription(
            domain_id=domain_id, subscription_id=subscription_id
        )
        if (
            response.subscription is not None
            and response.subscription.status == SubscriptionStatus.INACTIVE
        ):
            return
        await asyncio.sleep(_SUBSCRIPTION_POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"Subscription {subscription_id} did not reach INACTIVE in time")


async def _create_connecthealth_resources(
    client: AsyncConnectHealthClient, domain_name: str
) -> tuple[str, str]:
    """Create a ConnectHealth Domain and an ACTIVE Subscription.

    Args:
        client: A ConnectHealth client.
        domain_name: The name of the Domain to create.

    Returns:
        Tuple of (domain_id, subscription_id).
    """
    domain_response = await client.create_domain(name=domain_name, tags=_TAGS)
    domain_id = domain_response.domain_id

    subscription_response = await client.create_subscription(domain_id=domain_id)
    return domain_id, subscription_response.subscription_id


async def _delete_connecthealth_resources(
    client: AsyncConnectHealthClient, domain_id: str | None, subscription_id: str | None
) -> None:
    """Deactivate the Subscription, then delete the Domain.

    Args:
        client: A ConnectHealth client.
        domain_id: The Domain ID to delete, or None if creation failed.
        subscription_id: The Subscription ID to deactivate, or None if
            creation failed.
    """
    if domain_id and subscription_id:
        await client.deactivate_subscription(
            domain_id=domain_id, subscription_id=subscription_id
        )
        await _wait_for_subscription_inactive(client, domain_id, subscription_id)
    if domain_id:
        await client.delete_domain(domain_id=domain_id)


def _create_s3_bucket(s3_client: Any, bucket_name: str) -> None:
    """Create and tag the S3 bucket used by the streaming session.

    Args:
        s3_client: A boto3 S3 client.
        bucket_name: The name of the S3 bucket to create.
    """
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={
            "Tags": [{"Key": k, "Value": v} for k, v in _TAGS.items()],
        },
    )


def _delete_s3_bucket(s3_client: Any, bucket_name: str) -> None:
    """Empty and delete the S3 bucket.

    Args:
        s3_client: A boto3 S3 client.
        bucket_name: The name of the S3 bucket to delete.
    """
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get("Contents")
            if not objects:
                continue
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
            )
        s3_client.delete_bucket(Bucket=bucket_name)
    except s3_client.exceptions.NoSuchBucket:
        pass


@pytest.fixture(scope="session")
async def connecthealth_resources():
    """Create ConnectHealth resources for the test session and delete them after."""
    unique_suffix = uuid.uuid4().hex[:16]
    domain_name = f"integ-test-connecthealth-domain-{unique_suffix}"
    bucket_name = f"integ-test-connecthealth-bucket-{unique_suffix}"

    s3_client = boto3.client("s3", region_name=REGION)
    async with await create_connecthealth_client(REGION) as client:
        domain_id: str | None = None
        subscription_id: str | None = None
        try:
            _create_s3_bucket(s3_client, bucket_name)
            domain_id, subscription_id = await _create_connecthealth_resources(
                client, domain_name
            )
            output_s3_uri = f"s3://{bucket_name}/clinical-notes/"
            yield domain_id, subscription_id, output_s3_uri
        finally:
            await _delete_connecthealth_resources(client, domain_id, subscription_id)
            _delete_s3_bucket(s3_client, bucket_name)
