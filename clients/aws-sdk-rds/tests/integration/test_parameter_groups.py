# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""DB parameter group lifecycle and query-protocol list round trips."""

import pytest
from aws_sdk_rds.aio.client import AsyncRDSClient
from aws_sdk_rds.models import (
    AddTagsToResourceInput,
    ApplyMethod,
    DBParameterGroup,
    DBParameterGroupNotFoundFault,
    DeleteDBParameterGroupInput,
    DescribeDBParameterGroupsInput,
    DescribeDBParametersInput,
    DescribeDBParametersOutput,
    ListTagsForResourceInput,
    ModifyDBParameterGroupInput,
    Parameter,
    Tag,
)
from waiters import wait_until, wait_until_gone

from .conftest import PARAMETER_GROUP_FAMILY


async def test_parameter_group_create_describe_delete(
    rds: AsyncRDSClient, parameter_group: DBParameterGroup
) -> None:
    """A created group is described with its fields and is gone after deletion."""
    name = parameter_group.db_parameter_group_name
    assert name is not None
    assert parameter_group.db_parameter_group_family == PARAMETER_GROUP_FAMILY
    assert parameter_group.description == "aws-sdk-python integration test"

    described = await wait_until(
        lambda: rds.describe_db_parameter_groups(
            DescribeDBParameterGroupsInput(db_parameter_group_name=name)
        ),
        retry_on=(DBParameterGroupNotFoundFault,),
        interval=2,
        timeout=60,
    )
    assert [g.db_parameter_group_arn for g in described.db_parameter_groups or []] == [
        parameter_group.db_parameter_group_arn
    ]

    await rds.delete_db_parameter_group(
        DeleteDBParameterGroupInput(db_parameter_group_name=name)
    )
    await wait_until_gone(
        lambda: rds.describe_db_parameter_groups(
            DescribeDBParameterGroupsInput(db_parameter_group_name=name)
        ),
        gone_on=(DBParameterGroupNotFoundFault,),
        interval=2,
        timeout=60,
    )
    with pytest.raises(DBParameterGroupNotFoundFault) as caught:
        await rds.describe_db_parameter_groups(
            DescribeDBParameterGroupsInput(db_parameter_group_name=name)
        )
    assert caught.value.response_metadata.http_status_code == 404


async def test_modified_parameters_round_trip(
    rds: AsyncRDSClient, parameter_group: DBParameterGroup
) -> None:
    """A list of parameters sent to ModifyDBParameterGroup is returned as user-sourced."""
    name = parameter_group.db_parameter_group_name
    assert name is not None
    desired = {"wait_timeout": "600", "net_read_timeout": "45"}

    modified = await rds.modify_db_parameter_group(
        ModifyDBParameterGroupInput(
            db_parameter_group_name=name,
            parameters=[
                Parameter(
                    parameter_name=key,
                    parameter_value=value,
                    apply_method=ApplyMethod.IMMEDIATE,
                )
                for key, value in desired.items()
            ],
        )
    )
    assert modified.db_parameter_group_name == name

    def user_parameters(
        result: DescribeDBParametersOutput,
    ) -> dict[str | None, str | None]:
        return {p.parameter_name: p.parameter_value for p in result.parameters or []}

    described = await wait_until(
        lambda: rds.describe_db_parameters(
            DescribeDBParametersInput(db_parameter_group_name=name, source="user")
        ),
        lambda result: user_parameters(result) == desired,
        interval=2,
        timeout=60,
    )
    assert user_parameters(described) == desired


async def test_tags_round_trip(
    rds: AsyncRDSClient, parameter_group: DBParameterGroup
) -> None:
    """Tags set at creation and added later are all listed for the resource ARN."""
    arn = parameter_group.db_parameter_group_arn
    assert arn is not None

    await rds.add_tags_to_resource(
        AddTagsToResourceInput(
            resource_name=arn,
            tags=[Tag(key="Owner", value="sdk team"), Tag(key="Empty", value="")],
        )
    )

    expected = {"Purpose": "IntegTest", "Owner": "sdk team", "Empty": ""}
    listed = await wait_until(
        lambda: rds.list_tags_for_resource(ListTagsForResourceInput(resource_name=arn)),
        lambda result: {t.key: t.value for t in result.tag_list or []} == expected,
        interval=2,
        timeout=60,
    )
    assert {t.key: t.value for t in listed.tag_list or []} == expected


async def test_describe_parameters_paginates_with_marker(rds: AsyncRDSClient) -> None:
    """Paging through a default group's parameters by marker yields distinct names."""
    names: list[str] = []
    marker: str | None = None
    pages = 0
    while pages < 3:
        page = await rds.describe_db_parameters(
            DescribeDBParametersInput(
                db_parameter_group_name=f"default.{PARAMETER_GROUP_FAMILY}",
                max_records=20,
                marker=marker,
            )
        )
        pages += 1
        page_names = [p.parameter_name for p in page.parameters or []]
        assert 0 < len(page_names) <= 20
        names.extend(n for n in page_names if n is not None)
        marker = page.marker
        if marker is None:
            break

    assert pages > 1
    assert len(names) == len(set(names))
