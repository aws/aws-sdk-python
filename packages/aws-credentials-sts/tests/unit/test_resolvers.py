#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from collections.abc import Callable, Mapping

import pytest
from aws_credentials_sts.resolvers import _account_id_from_arn, _resolve_sts_region
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig


@pytest.fixture
def merged_config() -> Callable[..., MergedConfig]:
    def _build(profiles: Mapping[str, Mapping[str, str]]) -> MergedConfig:
        sections = {
            name: Section(properties=dict(properties))
            for name, properties in profiles.items()
        }
        return MergedConfig(StandardizedOutput(profiles=sections), StandardizedOutput())

    return _build


@pytest.mark.parametrize(
    ("env_aws_region", "env_aws_default_region", "profile_region", "expected"),
    [
        (None, None, None, "us-east-1"),
        ("us-west-2", None, "eu-west-1", "us-west-2"),
        (None, "ap-south-1", None, "ap-south-1"),
        (None, None, "eu-west-1", "eu-west-1"),
    ],
)
def test_resolve_sts_region(
    env_aws_region: str | None,
    env_aws_default_region: str | None,
    profile_region: str | None,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    merged_config: Callable[..., MergedConfig],
) -> None:
    for name, value in (
        ("AWS_REGION", env_aws_region),
        ("AWS_DEFAULT_REGION", env_aws_default_region),
    ):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    config_file = merged_config(
        {"default": {"region": profile_region}} if profile_region else {}
    )

    region = _resolve_sts_region(config_file=config_file, profile_name="default")

    assert region == expected


@pytest.mark.parametrize(
    "arn,expected",
    [
        ("arn:aws:sts::123456789012:assumed-role/MyRole/session", "123456789012"),
        ("arn:aws:sts:::assumed-role/MyRole/session", None),  # empty account field
        ("not-an-arn", None),  # too few segments
        (None, None),
    ],
)
def test_account_id_from_arn(arn: str | None, expected: str | None) -> None:
    assert _account_id_from_arn(arn) == expected
