# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Security group lifecycle and nested query-protocol structures."""

from aws_sdk_ec2.aio.client import AsyncEC2Client
from aws_sdk_ec2.models import (
    AuthorizeSecurityGroupIngressInput,
    DescribeSecurityGroupRulesInput,
    DescribeSecurityGroupsInput,
    Filter,
    IpPermission,
    IpRange,
)
from waiters import wait_until

from . import EVENTUAL_ERRORS, PURPOSE_TAG


async def test_authorized_ingress_round_trips_nested_permissions(
    ec2: AsyncEC2Client, security_group: str, default_vpc_id: str
) -> None:
    """Ingress rules with nested CIDR lists come back from describe as sent."""
    authorized = await ec2.authorize_security_group_ingress(
        AuthorizeSecurityGroupIngressInput(
            group_id=security_group,
            ip_permissions=[
                IpPermission(
                    ip_protocol="tcp",
                    from_port=8080,
                    to_port=8081,
                    ip_ranges=[
                        IpRange(cidr_ip="10.0.0.0/24", description="first range"),
                        IpRange(cidr_ip="10.1.0.0/24", description="second range"),
                    ],
                ),
                IpPermission(
                    ip_protocol="udp",
                    from_port=5353,
                    to_port=5353,
                    ip_ranges=[IpRange(cidr_ip="192.168.0.0/16")],
                ),
            ],
        )
    )
    assert authorized.return_ is True
    assert len(authorized.security_group_rules or []) == 3

    described = await wait_until(
        lambda: ec2.describe_security_groups(
            DescribeSecurityGroupsInput(
                filters=[
                    Filter(name="group-id", values=[security_group]),
                    Filter(name="tag:Purpose", values=["IntegTest"]),
                ]
            )
        ),
        lambda found: any(
            len(g.ip_permissions or []) == 2 for g in found.security_groups or []
        ),
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )
    [group] = described.security_groups or []
    assert group.group_id == security_group
    assert group.vpc_id == default_vpc_id
    assert group.description == "aws-sdk-python integration test"
    assert {(t.key, t.value) for t in group.tags or []} == {
        (PURPOSE_TAG.key, PURPOSE_TAG.value)
    }

    ranges = {
        (p.ip_protocol, p.from_port, p.to_port): {
            (r.cidr_ip, r.description) for r in p.ip_ranges or []
        }
        for p in group.ip_permissions or []
    }
    assert ranges == {
        ("tcp", 8080, 8081): {
            ("10.0.0.0/24", "first range"),
            ("10.1.0.0/24", "second range"),
        },
        ("udp", 5353, 5353): {("192.168.0.0/16", None)},
    }


async def test_security_group_rules_listed_by_group_filter(
    ec2: AsyncEC2Client, security_group: str
) -> None:
    """Rules fetched through a group-id filter include the ingress rule just added."""
    await ec2.authorize_security_group_ingress(
        AuthorizeSecurityGroupIngressInput(
            group_id=security_group,
            ip_protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_ip="10.2.0.0/16",
        )
    )

    rules = await wait_until(
        lambda: ec2.describe_security_group_rules(
            DescribeSecurityGroupRulesInput(
                filters=[Filter(name="group-id", values=[security_group])]
            )
        ),
        lambda found: any(not r.is_egress for r in found.security_group_rules or []),
        retry_on=EVENTUAL_ERRORS,
        interval=2,
        timeout=60,
    )

    ingress = [r for r in rules.security_group_rules or [] if not r.is_egress]
    assert [(r.ip_protocol, r.from_port, r.to_port, r.cidr_ipv4) for r in ingress] == [
        ("tcp", 443, 443, "10.2.0.0/16")
    ]
    assert all(r.group_id == security_group for r in rules.security_group_rules or [])
