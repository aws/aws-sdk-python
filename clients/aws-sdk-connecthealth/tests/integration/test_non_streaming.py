# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming operations for ConnectHealth."""

from aws_sdk_connecthealth.models import (
    DomainStatus,
    EncryptionType,
    GetDomainOutput,
    GetSubscriptionOutput,
    ListDomainsOutput,
    ListSubscriptionsOutput,
    SubscriptionStatus,
)

from . import REGION, create_connecthealth_client


async def test_list_domains(connecthealth_resources) -> None:
    """Test non-streaming ListDomains operation."""
    _ = connecthealth_resources
    async with await create_connecthealth_client(REGION) as client:
        response = await client.list_domains()

        assert isinstance(response, ListDomainsOutput)
        assert response.domains is not None
        assert len(response.domains) >= 1


async def test_get_domain(connecthealth_resources) -> None:
    """Test non-streaming GetDomain operation."""
    domain_id, _, _ = connecthealth_resources
    async with await create_connecthealth_client(REGION) as client:
        response = await client.get_domain(domain_id=domain_id)

        assert isinstance(response, GetDomainOutput)
        assert response.domain_id == domain_id
        assert response.status == DomainStatus.ACTIVE
        assert response.name is not None
        assert response.name.startswith("integ-test-connecthealth-domain-")
        assert response.arn is not None
        assert response.created_at is not None
        assert response.encryption_context is not None
        assert (
            response.encryption_context.encryption_type == EncryptionType.AWS_OWNED_KEY
        )
        assert response.tags == {"Purpose": "IntegTest"}


async def test_list_subscriptions(connecthealth_resources) -> None:
    """Test non-streaming ListSubscriptions operation."""
    domain_id, subscription_id, _ = connecthealth_resources
    async with await create_connecthealth_client(REGION) as client:
        response = await client.list_subscriptions(domain_id=domain_id)

        assert isinstance(response, ListSubscriptionsOutput)
        assert response.subscriptions is not None
        assert len(response.subscriptions) == 1

        sub = response.subscriptions[0]
        assert sub.subscription_id == subscription_id
        assert sub.domain_id == domain_id


async def test_get_subscription(connecthealth_resources) -> None:
    """Test non-streaming GetSubscription operation."""
    domain_id, subscription_id, _ = connecthealth_resources
    async with await create_connecthealth_client(REGION) as client:
        response = await client.get_subscription(
            domain_id=domain_id, subscription_id=subscription_id
        )

        assert isinstance(response, GetSubscriptionOutput)
        assert response.subscription is not None
        assert response.subscription.subscription_id == subscription_id
        assert response.subscription.domain_id == domain_id
        assert response.subscription.status == SubscriptionStatus.ACTIVE
        assert response.subscription.arn is not None
        assert response.subscription.created_at is not None
        assert response.subscription.last_updated_at is not None
