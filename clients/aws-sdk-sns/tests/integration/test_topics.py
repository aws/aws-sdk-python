# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Topic lifecycle, from JS v3 sns-features.e2e."""

from aws_sdk_sns.aio.client import AsyncSNSClient
from aws_sdk_sns.models import (
    GetTopicAttributesInput,
    ListTagsForResourceInput,
    ListTopicsInput,
    NotFoundException,
    SetTopicAttributesInput,
    Tag,
    TagResourceInput,
    UntagResourceInput,
)
from waiters import wait_until

from .conftest import TopicFactory


async def test_created_topic_appears_in_paginated_list_topics(
    sns: AsyncSNSClient, topic_arn: str
) -> None:
    """A new topic is eventually found by following ListTopics pagination tokens."""
    assert await wait_until(
        lambda: _topic_is_listed(sns, topic_arn), lambda found: found, interval=2
    )


async def test_tags_round_trip_through_create_tag_and_untag(
    sns: AsyncSNSClient, make_topic: TopicFactory
) -> None:
    """Tags set at creation, added with TagResource and removed with UntagResource read back."""
    arn = make_topic([Tag(key="Origin", value="create")])

    await sns.tag_resource(
        TagResourceInput(resource_arn=arn, tags=[Tag(key="Added", value="later")])
    )
    tags = await wait_until(
        lambda: sns.list_tags_for_resource(ListTagsForResourceInput(resource_arn=arn)),
        lambda out: (
            {tag.key for tag in out.tags or []} == {"Purpose", "Origin", "Added"}
        ),
        retry_on=(NotFoundException,),
        interval=2,
    )
    assert {(tag.key, tag.value) for tag in tags.tags or []} == {
        ("Purpose", "IntegTest"),
        ("Origin", "create"),
        ("Added", "later"),
    }

    await sns.untag_resource(UntagResourceInput(resource_arn=arn, tag_keys=["Origin"]))
    tags = await wait_until(
        lambda: sns.list_tags_for_resource(ListTagsForResourceInput(resource_arn=arn)),
        lambda out: {tag.key for tag in out.tags or []} == {"Purpose", "Added"},
        interval=2,
    )
    assert {tag.key for tag in tags.tags or []} == {"Purpose", "Added"}


async def test_set_topic_attributes_round_trip(
    sns: AsyncSNSClient, topic_arn: str
) -> None:
    """A DisplayName written with SetTopicAttributes is returned by GetTopicAttributes."""
    await wait_until(
        lambda: sns.get_topic_attributes(GetTopicAttributesInput(topic_arn=topic_arn)),
        retry_on=(NotFoundException,),
        interval=2,
    )
    await sns.set_topic_attributes(
        SetTopicAttributesInput(
            topic_arn=topic_arn, attribute_name="DisplayName", attribute_value="integ"
        )
    )
    output = await wait_until(
        lambda: sns.get_topic_attributes(GetTopicAttributesInput(topic_arn=topic_arn)),
        lambda out: (out.attributes or {}).get("DisplayName") == "integ",
        interval=2,
    )
    attributes = output.attributes or {}
    assert attributes["TopicArn"] == topic_arn
    assert attributes["DisplayName"] == "integ"


async def _topic_is_listed(sns: AsyncSNSClient, topic_arn: str) -> bool:
    token: str | None = None
    while True:
        page = await sns.list_topics(ListTopicsInput(next_token=token))
        if topic_arn in {topic.topic_arn for topic in page.topics or []}:
            return True
        token = page.next_token
        if token is None:
            return False
