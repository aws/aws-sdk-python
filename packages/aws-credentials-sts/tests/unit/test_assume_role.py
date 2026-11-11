#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from collections.abc import Callable, Mapping

import pytest
from aws_credentials_sts._assume_role import (
    AssumeRoleConfigurationError,
    _account_id_from_arn,
    is_assume_role_profile,
    plan_profile,
    resolve_sts_region,
)
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig

ASSUMED_ROLE_ARN = "arn:aws:sts::123456789012:assumed-role/MyRole/session"
ROLE_ARN = "arn:aws:iam::123456789012:role/MyRole"
TOKEN_FILE = "/var/run/secrets/token"


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
def testresolve_sts_region(
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

    region = resolve_sts_region(config_file=config_file, profile_name="default")

    assert region == expected


@pytest.mark.parametrize(
    "arn,expected",
    [
        (ASSUMED_ROLE_ARN, "123456789012"),
        ("arn:aws:sts:::assumed-role/MyRole/session", None),  # empty account field
        ("not-an-arn", None),  # too few segments
        (None, None),
    ],
)
def test_account_id_from_arn(arn: str | None, expected: str | None) -> None:
    assert _account_id_from_arn(arn) == expected


@pytest.mark.parametrize(
    ("profile", "expected"),
    [
        ({"role_arn": ROLE_ARN, "source_profile": "base"}, True),
        ({"role_arn": ROLE_ARN, "credential_source": "Environment"}, True),
        # Left to AssumeRole so it reports the missing source.
        ({"role_arn": ROLE_ARN}, True),
        # A web identity profile.
        ({"role_arn": ROLE_ARN, "web_identity_token_file": TOKEN_FILE}, False),
        (
            {
                "role_arn": ROLE_ARN,
                "web_identity_token_file": TOKEN_FILE,
                "source_profile": "base",
            },
            True,
        ),
        ({"web_identity_token_file": TOKEN_FILE}, False),
        # A blank token file counts as unset, so this is a role without a source.
        ({"role_arn": ROLE_ARN, "web_identity_token_file": ""}, True),
    ],
)
def test_is_assume_role_profile(
    profile: dict[str, str],
    expected: bool,
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"default": profile})

    assert is_assume_role_profile(config_file, "default") is expected


def test_web_identity_source_profile_is_reported_as_unsupported(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "top": {"role_arn": ROLE_ARN, "source_profile": "wid"},
            "wid": {"role_arn": ROLE_ARN, "web_identity_token_file": TOKEN_FILE},
        }
    )

    # The source profile is a web identity profile, not an AssumeRole profile that
    # lacks a source, so the error doesn't suggest adding a source to it.
    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Source profile 'wid' has no supported credential source",
    ):
        plan_profile(config_file, "top")
