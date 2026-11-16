# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Queue lifecycle and configuration, from JS v3 sqs-queues-features.e2e."""

from aws_sdk_sqs.aio.client import AsyncSQSClient
from aws_sdk_sqs.models import (
    CreateQueueInput,
    GetQueueAttributesInput,
    GetQueueUrlInput,
    ListQueuesInput,
    ListQueueTagsInput,
    QueueDoesNotExist,
    SetQueueAttributesInput,
    TagQueueInput,
)

from waiters import wait_until

from . import QUEUE_PREFIX, unique_queue_name
from .conftest import QueueFactory


async def test_create_queue_is_idempotent_and_resolvable_by_name(
    sqs: AsyncSQSClient, make_queue: QueueFactory
) -> None:
    """Creating a queue twice with identical attributes returns one URL that GetQueueUrl also finds."""
    name = unique_queue_name()
    url = await make_queue(name, {"VisibilityTimeout": "45"})

    again = await sqs.create_queue(
        CreateQueueInput(queue_name=name, attributes={"VisibilityTimeout": "45"})
    )
    assert again.queue_url == url

    resolved = await wait_until(
        lambda: sqs.get_queue_url(GetQueueUrlInput(queue_name=name)),
        retry_on=(QueueDoesNotExist,),
        interval=2,
    )
    assert resolved.queue_url == url


async def test_list_queues_pages_through_prefix_matches(
    sqs: AsyncSQSClient, make_queue: QueueFactory
) -> None:
    """Listing with MaxResults=1 and a unique prefix yields every created queue across pages."""
    infix = unique_queue_name("list-")
    created = {await make_queue(f"{infix}{i}") for i in range(3)}

    async def list_all() -> set[str]:
        found: set[str] = set()
        token: str | None = None
        while True:
            page = await sqs.list_queues(
                ListQueuesInput(
                    queue_name_prefix=infix, max_results=1, next_token=token
                )
            )
            assert len(page.queue_urls or []) <= 1
            found.update(page.queue_urls or [])
            token = page.next_token
            if token is None:
                return found

    # Listing is eventually consistent, so new queues may be missing at first.
    found = await wait_until(
        list_all, lambda urls: urls == created, interval=5, timeout=60
    )
    assert found == created
    assert all(url.rsplit("/", 1)[-1].startswith(QUEUE_PREFIX) for url in found)


async def test_queue_attributes_and_tags_round_trip(
    sqs: AsyncSQSClient, queue_url: str
) -> None:
    """Attributes set with SetQueueAttributes and tags added with TagQueue read back."""
    await sqs.set_queue_attributes(
        SetQueueAttributesInput(
            queue_url=queue_url,
            attributes={"VisibilityTimeout": "77", "DelaySeconds": "3"},
        )
    )
    await sqs.tag_queue(TagQueueInput(queue_url=queue_url, tags={"Extra": "yes"}))

    # Attribute changes can take up to a minute to propagate.
    output = await wait_until(
        lambda: sqs.get_queue_attributes(
            GetQueueAttributesInput(queue_url=queue_url, attribute_names=["All"])
        ),
        lambda read: (
            (read.attributes or {}).get("VisibilityTimeout") == "77"
            and (read.attributes or {}).get("DelaySeconds") == "3"
        ),
        interval=5,
        timeout=90,
    )
    attributes = output.attributes or {}
    assert attributes["VisibilityTimeout"] == "77"
    assert attributes["DelaySeconds"] == "3"
    assert attributes["QueueArn"].endswith(":" + queue_url.rsplit("/", 1)[-1])

    expected_tags = {"Purpose": "IntegTest", "Extra": "yes"}
    tags = await wait_until(
        lambda: sqs.list_queue_tags(ListQueueTagsInput(queue_url=queue_url)),
        lambda read: read.tags == expected_tags,
        interval=2,
    )
    assert tags.tags == {"Purpose": "IntegTest", "Extra": "yes"}
