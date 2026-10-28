# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import pytest
from aws_credentials_imds.client import IMDSConfigurationError
from aws_credentials_imds.aio.providers import Ec2InstanceMetadataProvider
from aws_credentials_imds.aio.resolvers import IMDSCredentialsResolver
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_aws_core.aio.identity.chain.provider import ChainSetup
from smithy_core.interfaces.identity import Identity

_ENDPOINT_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT"
_ENDPOINT_MODE_ENV = "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE"
_DISABLED_ENV = "AWS_EC2_METADATA_DISABLED"
_PROFILE_NAME_ENV = "AWS_EC2_INSTANCE_PROFILE_NAME"

_ALL_ENV = (
    _ENDPOINT_ENV,
    _ENDPOINT_MODE_ENV,
    _DISABLED_ENV,
    _PROFILE_NAME_ENV,
)


class OtherIdentity(Identity):
    """A non-AWS identity type used to verify the provider ignores unknown types."""


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure host environment never leaks IMDS config into the tests.
    for name in _ALL_ENV:
        monkeypatch.delenv(name, raising=False)


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
        profile_name: str | None = "default",
    ) -> ChainSetup:
        setup = ChainSetup(config_file=config_file, profile_name=profile_name)
        setup.set_current_provider(provider)
        await provider.setup(identity_type, setup)
        return setup

    return _setup


def _only_resolver(setup: ChainSetup) -> IMDSCredentialsResolver:
    assert len(setup.resolvers) == 1
    resolver = setup.resolvers[0].resolver
    assert isinstance(resolver, IMDSCredentialsResolver)
    return resolver


def test_provider_metadata() -> None:
    provider = Ec2InstanceMetadataProvider()

    assert provider.name == StandardProvider.EC2_INSTANCE_METADATA.canonical_name
    assert provider.ordering == Standard(slot=StandardProvider.EC2_INSTANCE_METADATA)


async def test_ignores_non_aws_identity_type(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
) -> None:
    setup = await setup_provider(
        Ec2InstanceMetadataProvider(), identity_type=OtherIdentity
    )

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_registers_non_terminal_resolver(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
) -> None:
    setup = await setup_provider(Ec2InstanceMetadataProvider())

    assert not setup.terminal
    assert len(setup.resolvers) == 1
    assert setup.resolvers[0].provider_name == (
        StandardProvider.EC2_INSTANCE_METADATA.canonical_name
    )
    assert isinstance(setup.resolvers[0].resolver, IMDSCredentialsResolver)


@pytest.mark.parametrize("value", ["true", "True", "TRUE"])
async def test_disabled_env_skips_registration(
    value: str,
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_DISABLED_ENV, value)

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_disabled_profile_skips_registration(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config = merged_config({"default": {"disable_ec2_metadata": "true"}})

    setup = await setup_provider(
        Ec2InstanceMetadataProvider(), config_file=config, profile_name="default"
    )

    assert setup.resolvers == ()


async def test_disabled_false_still_registers(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_DISABLED_ENV, "false")

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    assert len(setup.resolvers) == 1


async def test_endpoint_mode_from_env(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_MODE_ENV, "IPv6")

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    config = _only_resolver(setup)._config
    assert config.endpoint_mode == "IPv6"
    assert config.endpoint_uri.host == config._HOST_MAPPING["IPv6"]


async def test_endpoint_mode_is_case_insensitive(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_MODE_ENV, "ipv6")

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    assert _only_resolver(setup)._config.endpoint_mode == "IPv6"


async def test_endpoint_mode_env_overrides_profile(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_MODE_ENV, "IPv6")
    config = merged_config({"default": {"ec2_metadata_service_endpoint_mode": "IPv4"}})

    setup = await setup_provider(Ec2InstanceMetadataProvider(), config_file=config)

    assert _only_resolver(setup)._config.endpoint_mode == "IPv6"


async def test_endpoint_mode_from_profile(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config = merged_config({"default": {"ec2_metadata_service_endpoint_mode": "IPv6"}})

    setup = await setup_provider(Ec2InstanceMetadataProvider(), config_file=config)

    assert _only_resolver(setup)._config.endpoint_mode == "IPv6"


async def test_invalid_endpoint_mode_raises(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_MODE_ENV, "IPv5")

    with pytest.raises(
        IMDSConfigurationError, match="Invalid IMDS endpoint mode 'IPv5'"
    ):
        await setup_provider(Ec2InstanceMetadataProvider())


async def test_endpoint_from_env(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_ENV, "http://169.254.169.200:8080")

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    endpoint = _only_resolver(setup)._config.endpoint_uri
    assert endpoint.scheme == "http"
    assert endpoint.host == "169.254.169.200"
    assert endpoint.port == 8080


async def test_endpoint_env_overrides_profile(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENDPOINT_ENV, "http://169.254.169.200")
    config = merged_config(
        {"default": {"ec2_metadata_service_endpoint": "http://169.254.169.111"}}
    )

    setup = await setup_provider(Ec2InstanceMetadataProvider(), config_file=config)

    assert _only_resolver(setup)._config.endpoint_uri.host == "169.254.169.200"


async def test_endpoint_from_profile(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config = merged_config(
        {"default": {"ec2_metadata_service_endpoint": "http://169.254.169.111"}}
    )

    setup = await setup_provider(Ec2InstanceMetadataProvider(), config_file=config)

    assert _only_resolver(setup)._config.endpoint_uri.host == "169.254.169.111"


async def test_invalid_endpoint_raises(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Missing scheme is not a valid endpoint URI.
    monkeypatch.setenv(_ENDPOINT_ENV, "169.254.169.254")

    with pytest.raises(IMDSConfigurationError, match="Invalid IMDS endpoint URI"):
        await setup_provider(Ec2InstanceMetadataProvider())


async def test_profile_name_from_env(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_PROFILE_NAME_ENV, "my-profile")

    setup = await setup_provider(Ec2InstanceMetadataProvider())

    assert _only_resolver(setup)._config.ec2_instance_profile_name == "my-profile"


async def test_profile_name_from_profile(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    merged_config: Callable[..., MergedConfig],
) -> None:
    config = merged_config({"default": {"ec2_instance_profile_name": "my-profile"}})

    setup = await setup_provider(Ec2InstanceMetadataProvider(), config_file=config)

    assert _only_resolver(setup)._config.ec2_instance_profile_name == "my-profile"


async def test_blank_profile_name_raises(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_PROFILE_NAME_ENV, "   ")

    with pytest.raises(
        IMDSConfigurationError,
        match="The configured EC2 instance profile name must not be blank",
    ):
        await setup_provider(Ec2InstanceMetadataProvider())
