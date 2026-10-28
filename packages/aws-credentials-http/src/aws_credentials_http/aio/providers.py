# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_aws_core.aio.identity.chain.provider import ChainSetup
from smithy_core.interfaces.identity import Identity

from .resolvers import ContainerCredentialsResolver

_RELATIVE_URI = "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"
_FULL_URI = "AWS_CONTAINER_CREDENTIALS_FULL_URI"


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

    async def setup(
        self,
        identity_type: type[Identity],
        setup: ChainSetup,
    ) -> None:
        """Add a terminal resolver when a container endpoint is configured."""
        if identity_type is not AWSCredentialsIdentity:
            return
        if not os.getenv(_RELATIVE_URI) and not os.getenv(_FULL_URI):
            return
        setup.add_terminal_resolver(
            ContainerCredentialsResolver(http_client=setup.http_client)
        )
