# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Key pair lifecycle and tag round trips with filters."""

from aws_sdk_ec2.aio.client import AsyncEC2Client
from aws_sdk_ec2.models import (
    CreateKeyPairInput,
    CreateTagsInput,
    DeleteKeyPairInput,
    DeleteTagsInput,
    DescribeKeyPairsInput,
    DescribeSecurityGroupsInput,
    DescribeTagsInput,
    Filter,
    ResourceType,
    Tag,
    TagSpecification,
)
from waiters import wait_until

from . import EVENTUAL_ERRORS, PURPOSE_TAG, unique_name


async def test_key_pair_create_describe_delete(ec2: AsyncEC2Client) -> None:
    """A created key pair returns key material, is tagged and described, and is gone after deletion."""
    name = unique_name("key-")
    created = await ec2.create_key_pair(
        CreateKeyPairInput(
            key_name=name,
            key_type="ed25519",
            tag_specifications=[
                TagSpecification(
                    resource_type=ResourceType.KEY_PAIR, tags=[PURPOSE_TAG]
                )
            ],
        )
    )
    try:
        assert created.key_name == name
        assert created.key_pair_id and created.key_pair_id.startswith("key-")
        assert created.key_fingerprint
        assert created.key_material
        assert created.key_material.startswith("-----BEGIN")

        described = await wait_until(
            lambda: ec2.describe_key_pairs(
                DescribeKeyPairsInput(key_names=[name], include_public_key=True)
            ),
            retry_on=EVENTUAL_ERRORS,
            interval=2,
            timeout=60,
        )
        [info] = described.key_pairs or []
        assert info.key_pair_id == created.key_pair_id
        assert info.key_fingerprint == created.key_fingerprint
        assert info.key_type == "ed25519"
        assert info.public_key
        assert info.create_time is not None
        assert {(t.key, t.value) for t in info.tags or []} == {
            (PURPOSE_TAG.key, PURPOSE_TAG.value)
        }
    finally:
        await ec2.delete_key_pair(DeleteKeyPairInput(key_pair_id=created.key_pair_id))

    remaining = await wait_until(
        lambda: ec2.describe_key_pairs(
            DescribeKeyPairsInput(filters=[Filter(name="key-name", values=[name])])
        ),
        lambda found: not found.key_pairs,
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )
    assert not remaining.key_pairs


async def test_tags_created_filtered_and_deleted(
    ec2: AsyncEC2Client, security_group: str
) -> None:
    """Tags added to a resource are found by tag filters and removed again."""
    await ec2.create_tags(
        CreateTagsInput(
            resources=[security_group],
            tags=[Tag(key="Stage", value="alpha"), Tag(key="Empty", value="")],
        )
    )

    by_resource = await wait_until(
        lambda: ec2.describe_tags(
            DescribeTagsInput(
                filters=[Filter(name="resource-id", values=[security_group])]
            )
        ),
        lambda found: len(found.tags or []) == 3,
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )
    assert {(t.key, t.value) for t in by_resource.tags or []} == {
        ("Purpose", "IntegTest"),
        ("Stage", "alpha"),
        ("Empty", ""),
    }
    assert {t.resource_type for t in by_resource.tags or []} == {"security-group"}

    by_tag = await wait_until(
        lambda: ec2.describe_security_groups(
            DescribeSecurityGroupsInput(
                filters=[Filter(name="tag:Stage", values=["beta", "alpha"])]
            )
        ),
        lambda found: bool(found.security_groups),
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )
    assert [g.group_id for g in by_tag.security_groups or []] == [security_group]

    await ec2.delete_tags(
        DeleteTagsInput(
            resources=[security_group],
            tags=[Tag(key="Stage", value="alpha"), Tag(key="Empty", value="")],
        )
    )

    after = await wait_until(
        lambda: ec2.describe_tags(
            DescribeTagsInput(
                filters=[Filter(name="resource-id", values=[security_group])]
            )
        ),
        lambda found: len(found.tags or []) == 1,
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )
    assert {(t.key, t.value) for t in after.tags or []} == {("Purpose", "IntegTest")}
