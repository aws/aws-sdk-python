# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import Standard, StandardProvider
from smithy_aws_core.identity.chain.provider import ChainSetup
from smithy_core.interfaces.identity import Identity

from ._assume_role import is_assume_role_profile
from ._web_identity import WebIdentityConfig, env_config, profile_config
from .resolvers import (
    ProfileAssumeRoleCredentialsResolver,
    WebIdentityCredentialsResolver,
)


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

    def setup(self, identity_type: type[Identity], setup: ChainSetup) -> None:
        """Add a terminal resolver when the active profile assumes a role."""
        if identity_type is not AWSCredentialsIdentity:
            return
        profile_name = setup.profile_name
        config_file = setup.config_file
        if profile_name is None or config_file is None:
            return
        if is_assume_role_profile(config_file, profile_name):
            setup.add_terminal_resolver(
                ProfileAssumeRoleCredentialsResolver(
                    profile_name=profile_name,
                    config_file=config_file,
                    region_override=setup.region_override,
                    http_client=setup.http_client,
                )
            )


# TODO: Declare feature_ids on the web identity providers once smithy-aws-core
# releases the web identity feature IDs: CREDENTIALS_ENV_VARS_STS_WEB_ID_TOKEN and
# CREDENTIALS_STS_ASSUME_ROLE_WEB_ID for the environment provider, and
# CREDENTIALS_PROFILE_STS_WEB_ID_TOKEN and CREDENTIALS_STS_ASSUME_ROLE_WEB_ID for
# the profile provider.


class WebIdentityTokenEnvProvider:
    """Adds a web identity resolver configured by environment variables."""

    @property
    def name(self) -> str:
        """Return the canonical provider name."""
        return StandardProvider.WEB_IDENTITY_TOKEN_ENV.canonical_name

    @property
    def ordering(self) -> Standard:
        """Return the provider's standard chain position."""
        return Standard(slot=StandardProvider.WEB_IDENTITY_TOKEN_ENV)

    def setup(self, identity_type: type[Identity], setup: ChainSetup) -> None:
        """Add a terminal resolver when the web identity variables are set."""
        if identity_type is not AWSCredentialsIdentity:
            return
        if (config := env_config(setup)) is not None:
            setup.add_terminal_resolver(_web_identity_resolver(config, setup))


class ProfileWebIdentityProvider:
    """Adds a web identity resolver configured by the active profile."""

    @property
    def name(self) -> str:
        """Return the canonical provider name."""
        return StandardProvider.PROFILE_WEB_IDENTITY.canonical_name

    @property
    def ordering(self) -> Standard:
        """Return the provider's standard chain position."""
        return Standard(slot=StandardProvider.PROFILE_WEB_IDENTITY)

    def setup(self, identity_type: type[Identity], setup: ChainSetup) -> None:
        """Add a terminal resolver when the active profile sets a token file."""
        if identity_type is not AWSCredentialsIdentity:
            return
        if (config := profile_config(setup)) is not None:
            setup.add_terminal_resolver(_web_identity_resolver(config, setup))


def _web_identity_resolver(
    config: WebIdentityConfig, setup: ChainSetup
) -> WebIdentityCredentialsResolver:
    return WebIdentityCredentialsResolver(
        role_arn=config.role_arn,
        web_identity_token_file=config.web_identity_token_file,
        role_session_name=config.role_session_name,
        region=config.region,
        http_client=setup.http_client,
    )
