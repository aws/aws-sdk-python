# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.aio.identity.chain.provider import ChainSetup
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_core.interfaces.identity import Identity

from .resolvers import ProfileAssumeRoleCredentialsResolver

_ROLE_ARN = "role_arn"


class ProfileAssumeRoleProvider:
    """Adds an STS AssumeRole resolver to the credential chain."""

    @property
    def name(self) -> str:
        """Return the canonical provider name."""
        return StandardProvider.PROFILE_ASSUME_ROLE.canonical_name

    @property
    def ordering(self) -> Standard:
        """Return the provider's standard chain position."""
        return Standard(slot=StandardProvider.PROFILE_ASSUME_ROLE)

    async def setup(self, identity_type: type[Identity], setup: ChainSetup) -> None:
        """Add a terminal resolver when the active profile declares a role ARN."""
        if identity_type is not AWSCredentialsIdentity:
            return

        profile_name = setup.profile_name
        config_file = setup.config_file
        if (
            profile_name is None
            or config_file is None
            or config_file.get(profile_name, _ROLE_ARN) is None
        ):
            return

        setup.add_terminal_resolver(
            ProfileAssumeRoleCredentialsResolver(
                profile_name=profile_name,
                config_file=config_file,
                region_override=setup.region_override,
                http_client=setup.http_client,
            )
        )
