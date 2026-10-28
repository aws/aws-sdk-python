# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# pyright: reportPrivateUsage=false
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from aws_credentials_http.aio import ContainerCredentialsResolver, EcsContainerProvider
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_aws_core.aio.identity.chain.provider import ChainSetup
from smithy_core.interfaces.identity import Identity

_RELATIVE_URI = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
_FULL_URI = "AWS_CONTAINER_CREDENTIALS_FULL_URI"

_ALL_ENV = (
    _RELATIVE_URI,
    _FULL_URI,
)


class OtherIdentity(Identity):
    """A non-AWS identity type used to verify the provider ignores unknown types."""


@pytest.fixture(autouse=True)
def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure host environment never leaks container config into the tests.
    for name in _ALL_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def setup_provider() -> Callable[..., Awaitable[ChainSetup]]:
    async def _setup(
        provider: Any,
        *,
        identity_type: type[Identity] = AWSCredentialsIdentity,
    ) -> ChainSetup:
        setup = ChainSetup()
        setup.set_current_provider(provider)
        await provider.setup(identity_type, setup)
        return setup

    return _setup


def test_provider_metadata() -> None:
    provider = EcsContainerProvider()

    assert provider.name == StandardProvider.ECS_CONTAINER.canonical_name
    assert provider.ordering == Standard(slot=StandardProvider.ECS_CONTAINER)


async def test_ignores_non_aws_identity_type(
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_RELATIVE_URI, "/credentials")

    setup = await setup_provider(EcsContainerProvider(), identity_type=OtherIdentity)

    assert setup.resolvers == ()
    assert not setup.terminal


@pytest.mark.parametrize(
    ("relative_uri", "full_uri"),
    [
        (None, None),
        ("", None),
        (None, ""),
        ("", ""),
    ],
)
async def test_requires_configured_endpoint(
    relative_uri: str | None,
    full_uri: str | None,
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if relative_uri is not None:
        monkeypatch.setenv(_RELATIVE_URI, relative_uri)
    if full_uri is not None:
        monkeypatch.setenv(_FULL_URI, full_uri)

    setup = await setup_provider(EcsContainerProvider())

    assert setup.resolvers == ()
    assert not setup.terminal


@pytest.mark.parametrize(
    ("name", "value"),
    [
        (_RELATIVE_URI, "/credentials"),
        (_FULL_URI, "http://169.254.170.23/credentials"),
    ],
)
async def test_registers_terminal_resolver_for_env_vars(
    name: str,
    value: str,
    setup_provider: Callable[..., Awaitable[ChainSetup]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(name, value)

    setup = await setup_provider(EcsContainerProvider())

    assert setup.terminal
    assert len(setup.resolvers) == 1
    assert setup.resolvers[0].provider_name == "EcsContainer"
    resolver = setup.resolvers[0].resolver
    assert isinstance(resolver, ContainerCredentialsResolver)
