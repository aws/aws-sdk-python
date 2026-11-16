# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Region and zone discovery with list parameters, from JS v3 ec2-features.e2e."""

from aws_sdk_ec2.aio.client import AsyncEC2Client
from aws_sdk_ec2.models import (
    DescribeAvailabilityZonesInput,
    DescribeRegionsInput,
    Filter,
)

from . import REGION


async def test_describe_regions_filters_by_name_list(ec2: AsyncEC2Client) -> None:
    """A list of region names and a filter each narrow the result to the named regions."""
    everything = await ec2.describe_regions(DescribeRegionsInput())
    assert REGION in {r.region_name for r in everything.regions or []}

    by_names = await ec2.describe_regions(
        DescribeRegionsInput(region_names=[REGION, "us-east-2"])
    )
    assert {r.region_name for r in by_names.regions or []} == {REGION, "us-east-2"}

    by_filter = await ec2.describe_regions(
        DescribeRegionsInput(filters=[Filter(name="region-name", values=[REGION])])
    )
    regions = by_filter.regions or []
    assert [r.region_name for r in regions] == [REGION]
    assert regions[0].endpoint and REGION in regions[0].endpoint


async def test_describe_availability_zones_with_filters(ec2: AsyncEC2Client) -> None:
    """Multi-value filters return only available zones of the client's region."""
    zones = await ec2.describe_availability_zones(
        DescribeAvailabilityZonesInput(
            filters=[
                Filter(name="state", values=["available"]),
                Filter(name="zone-type", values=["availability-zone"]),
            ]
        )
    )

    assert len(zones.availability_zones or []) >= 2
    for zone in zones.availability_zones or []:
        assert zone.region_name == REGION
        assert zone.state == "available"
        assert zone.zone_name and zone.zone_name.startswith(REGION)
        assert zone.zone_id
