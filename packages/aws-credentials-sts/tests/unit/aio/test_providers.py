#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import pytest
from aws_credentials_sts.aio.providers import ProfileAssumeRoleProvider
from aws_credentials_sts.aio.resolvers import ProfileAssumeRoleCredentialsResolver
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.aio.identity.chain.provider import ChainSetup
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_core.interfaces.identity import Identity

ROLE_ARN = "arn:aws:iam::123456789012:role/MyRole"


class OtherIdentity(Identity):
    """A non-AWS identity type used to verify the provider ignores unknown types."""


@pytest.fixture
def merged_config() -> Callable[..., MergedConfig]:
    def _build(
        profiles: Mapping[str, Mapping[str, str]] | None = None,
    ) -> MergedConfig:
        sections = {
            name: Section(properties=dict(properties))
            for name, properties in (profiles or {}).items()
        }
        return MergedConfig(StandardizedOutput(profiles=sections), StandardizedOutput())

    return _build


@pytest.fixture
def setup_provider() -> Callable[..., Awaitable[ChainSetup]]:
    async def _setup(
        provider: Any,
        *,
        identity_type: type[Identity] = AWSCredentialsIdentity,
        config_file: MergedConfig | None = None,
        profile_name: str,
    ) -> ChainSetup:
        setup = ChainSetup(config_file=config_file, profile_name=profile_name)
        setup.set_current_provider(provider)
        await provider.setup(identity_type, setup)
        return setup

    return _setup


def test_provider_metadata() -> None:
    provider = ProfileAssumeRoleProvider()

    assert provider.name == StandardProvider.PROFILE_ASSUME_ROLE.canonical_name
    assert provider.ordering == Standard(slot=StandardProvider.PROFILE_ASSUME_ROLE)


async def test_ignores_non_aws_identity_type(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"default": {"role_arn": ROLE_ARN}})
    setup = await setup_provider(
        ProfileAssumeRoleProvider(),
        identity_type=OtherIdentity,
        config_file=config_file,
        profile_name="default",
    )

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_no_profile_name_skips(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
) -> None:
    setup = await setup_provider(ProfileAssumeRoleProvider(), profile_name=None)

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_profile_without_role_arn_skips(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"default": {"region": "us-east-1"}})
    setup = await setup_provider(
        ProfileAssumeRoleProvider(), config_file=config_file, profile_name="default"
    )

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_registers_terminal_resolver_for_role_arn(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "default": {"role_arn": ROLE_ARN, "source_profile": "base"},
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    setup = await setup_provider(
        ProfileAssumeRoleProvider(), config_file=config_file, profile_name="default"
    )

    assert setup.terminal
    assert len(setup.resolvers) == 1
    assert isinstance(setup.resolvers[0].resolver, ProfileAssumeRoleCredentialsResolver)
