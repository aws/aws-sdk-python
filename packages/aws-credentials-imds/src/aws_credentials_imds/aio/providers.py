# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.aio.identity.chain.provider import AsyncChainSetup
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_core.interfaces.identity import Identity

from .._imds import provider_config
from .resolvers import AsyncIMDSCredentialsResolver


class AsyncEc2InstanceMetadataProvider:
    """Adds an IMDS resolver to the async credential chain."""

    @property
    def name(self) -> str:
        """Return the canonical provider name."""
        return StandardProvider.EC2_INSTANCE_METADATA.canonical_name

    @property
    def ordering(self) -> Standard:
        """Return the provider's standard chain position."""
        return Standard(slot=StandardProvider.EC2_INSTANCE_METADATA)

    async def setup(
        self, identity_type: type[Identity], setup: AsyncChainSetup
    ) -> None:
        """Add IMDS as a non-terminal resolver unless disabled."""
        if identity_type is not AWSCredentialsIdentity:
            return
        config = provider_config(setup.config_file, setup.profile_name)
        if config is not None:
            setup.add_resolver(
                AsyncIMDSCredentialsResolver(
                    http_client=setup.http_client, config=config
                )
            )
