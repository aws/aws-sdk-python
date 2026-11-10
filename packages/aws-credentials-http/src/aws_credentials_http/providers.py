# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_aws_core.identity.chain.provider import ChainSetup
from smithy_core.interfaces.identity import Identity

from ._container import is_configured
from .resolvers import ContainerCredentialsResolver


class EcsContainerProvider:
    """Adds a container credential resolver to the credential chain."""

    @property
    def name(self) -> str:
        """Return the canonical provider name."""
        return StandardProvider.ECS_CONTAINER.canonical_name

    @property
    def ordering(self) -> Standard:
        """Return the provider's standard chain position."""
        return Standard(slot=StandardProvider.ECS_CONTAINER)

    def setup(self, identity_type: type[Identity], setup: ChainSetup) -> None:
        """Add a terminal resolver when a container endpoint is configured."""
        if identity_type is AWSCredentialsIdentity and is_configured():
            setup.add_terminal_resolver(
                ContainerCredentialsResolver(http_client=setup.http_client)
            )
