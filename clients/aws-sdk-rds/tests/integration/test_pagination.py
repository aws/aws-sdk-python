# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Marker pagination, from JS v3 rds-features.e2e."""

from aws_sdk_rds.aio.client import AsyncRDSClient
from aws_sdk_rds.models import DescribeReservedDBInstancesOfferingsInput
from waiters import wait_until


async def test_reserved_offerings_span_multiple_pages(rds: AsyncRDSClient) -> None:
    """Following the marker returns more than one page of distinct offerings."""
    offering_ids: list[str] = []
    marker: str | None = None
    pages = 0
    while pages < 3:
        page = await wait_until(
            lambda: rds.describe_reserved_db_instances_offerings(
                DescribeReservedDBInstancesOfferingsInput(max_records=20, marker=marker)
            ),
            lambda result: bool(result.reserved_db_instances_offerings),
            interval=2,
            timeout=60,
        )
        pages += 1
        offerings = page.reserved_db_instances_offerings or []
        assert 0 < len(offerings) <= 20
        offering_ids.extend(
            o.reserved_db_instances_offering_id
            for o in offerings
            if o.reserved_db_instances_offering_id is not None
        )
        marker = page.marker
        if marker is None:
            break

    assert pages > 1
    assert len(offering_ids) == len(set(offering_ids))
