# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Web identity logic shared by the sync and async resolvers and providers."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.exceptions import SmithyError, SmithyIdentityError
from smithy_core.interfaces.identity import IdentityResolver
from smithy_core.program import Program

from ._assume_role import _account_id_from_arn, resolve_sts_region  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from aws_sdk_sts.models import (
        AssumeRoleWithWebIdentityInput,
        AssumeRoleWithWebIdentityOutput,
    )
    from smithy_aws_core.aio.identity.chain.provider import AsyncChainSetup
    from smithy_aws_core.identity.chain.provider import ChainSetup
    from smithy_core.interfaces.retries import RetryBackoffStrategy

MAX_RETRIES = 3
"""The number of retries after the first attempt to fetch credentials."""

DEFAULT_ROLE_SESSION_NAME = f"aws-sdk-python-{uuid.uuid4().hex[:16]}"
"""The role session name used when none is configured.

It's generated once per process and shared by every web identity resolver.
"""

_WEB_IDENTITY_TOKEN_FILE_ENV = "AWS_WEB_IDENTITY_TOKEN_FILE"
_ROLE_ARN_ENV = "AWS_ROLE_ARN"
_ROLE_SESSION_NAME_ENV = "AWS_ROLE_SESSION_NAME"
_WEB_IDENTITY_TOKEN_FILE = "web_identity_token_file"
_ROLE_ARN = "role_arn"
_ROLE_SESSION_NAME = "role_session_name"


class WebIdentityConfigurationError(SmithyError):
    """Raised when web identity credential configuration is invalid."""


UNUSED_CREDENTIALS_MESSAGE = (
    "AssumeRoleWithWebIdentity is sent unsigned, so its STS client has no credentials."
)


class UnusedCredentialsResolver(
    IdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """The credentials resolver for the STS client that calls AssumeRoleWithWebIdentity.

    The call is never signed, so this is never asked for credentials. Setting it
    keeps the STS client from building its own default credential chain, which
    would include the web identity providers again.
    """

    def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        raise SmithyIdentityError(UNUSED_CREDENTIALS_MESSAGE)


@dataclass(frozen=True, kw_only=True)
class WebIdentityConfig:
    """The resolver settings a web identity provider found during chain setup."""

    role_arn: str
    web_identity_token_file: str
    role_session_name: str | None
    region: str


def env_config(setup: ChainSetup | AsyncChainSetup) -> WebIdentityConfig | None:
    """Read web identity settings from the environment, if they're complete.

    Returns None when either required variable is missing, so the chain moves on to
    the next source, or when a profile was selected explicitly, since that profile
    takes precedence over environment credentials.
    """
    if setup.profile_name is not None:
        return None

    web_identity_token_file = os.getenv(_WEB_IDENTITY_TOKEN_FILE_ENV)
    role_arn = os.getenv(_ROLE_ARN_ENV)
    if not web_identity_token_file or not role_arn:
        return None

    return WebIdentityConfig(
        role_arn=role_arn,
        web_identity_token_file=web_identity_token_file,
        role_session_name=os.getenv(_ROLE_SESSION_NAME_ENV) or None,
        region=setup.region_override or resolve_sts_region(),
    )


def profile_config(setup: ChainSetup | AsyncChainSetup) -> WebIdentityConfig | None:
    """Read web identity settings from the active profile, if it sets a token file.

    :raises WebIdentityConfigurationError: If the profile sets a token file but no
        role ARN.
    """
    config_file = setup.config_file
    profile_name = setup.profile_name
    if config_file is None or profile_name is None:
        return None

    web_identity_token_file = config_file.get(profile_name, _WEB_IDENTITY_TOKEN_FILE)
    # A blank value, such as a leftover 'web_identity_token_file =', counts as unset.
    if not web_identity_token_file:
        return None

    role_arn = config_file.get(profile_name, _ROLE_ARN)
    if role_arn is None:
        raise WebIdentityConfigurationError(
            f"Profile '{profile_name}' sets '{_WEB_IDENTITY_TOKEN_FILE}' but not "
            f"'{_ROLE_ARN}'."
        )

    return WebIdentityConfig(
        role_arn=role_arn,
        web_identity_token_file=web_identity_token_file,
        role_session_name=config_file.get(profile_name, _ROLE_SESSION_NAME),
        region=setup.region_override
        or resolve_sts_region(config_file=config_file, profile_name=profile_name),
    )


def read_token(path: Path, *, is_last_attempt: bool) -> str | None:
    """Read the OIDC token, stripped of surrounding whitespace.

    Returns None when the file couldn't be read, isn't ASCII, or is empty, and the
    read should be retried. On the last attempt, the failure is raised instead.
    """
    try:
        token = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as e:
        if is_last_attempt:
            raise SmithyIdentityError(
                f"Failed to read the web identity token file '{path}': {e}"
            ) from e
        return None
    if not token:
        if is_last_attempt:
            raise SmithyIdentityError(f"The web identity token file '{path}' is empty.")
        return None
    return token


def fetch_web_identity_credentials(
    *,
    read_token: Callable[..., Any],
    call_sts: Callable[[AssumeRoleWithWebIdentityInput], Any],
    sleep: Callable[[float], Any],
    backoff: RetryBackoffStrategy,
    web_identity_token_file: Path,
    role_arn: str,
    role_session_name: str,
) -> Program[AWSCredentialsIdentity]:
    """Call STS, retrying the failures the web identity SEP requires.

    A failure to read the token file and an ``ExpiredTokenException`` both read the
    token again before retrying. An ``IDPCommunicationError`` retries the STS call
    with the same token. Other errors are raised immediately.

    The sync and async resolvers run this with ``run_program`` and
    ``run_program_async``, passing in their own token read, STS call, and sleep.
    """
    from aws_sdk_sts.models import (
        ExpiredTokenException,
        IDPCommunicationErrorException,
    )

    token: str | None = None
    for attempt in range(MAX_RETRIES + 1):
        is_last_attempt = attempt == MAX_RETRIES
        if token is None:
            token = yield lambda: read_token(
                web_identity_token_file, is_last_attempt=is_last_attempt
            )
        if token is not None:
            request = web_identity_input(
                role_arn=role_arn,
                role_session_name=role_session_name,
                web_identity_token=token,
            )
            try:
                response = yield lambda: call_sts(request)
            except ExpiredTokenException:
                if is_last_attempt:
                    raise
                token = None  # Read a fresh token before retrying.
            except IDPCommunicationErrorException:
                if is_last_attempt:
                    raise
            else:
                return identity_from_response(response)
        delay = backoff.compute_next_backoff_delay(attempt + 1)
        yield lambda: sleep(delay)

    raise AssertionError("unreachable")


def web_identity_input(
    *, role_arn: str, role_session_name: str, web_identity_token: str
) -> AssumeRoleWithWebIdentityInput:
    from aws_sdk_sts.models import AssumeRoleWithWebIdentityInput

    return AssumeRoleWithWebIdentityInput(
        role_arn=role_arn,
        role_session_name=role_session_name,
        web_identity_token=web_identity_token,
    )


def identity_from_response(
    response: AssumeRoleWithWebIdentityOutput,
) -> AWSCredentialsIdentity:
    credentials = response.credentials
    if credentials is None:
        raise SmithyIdentityError(
            "STS AssumeRoleWithWebIdentity response did not contain credentials."
        )
    assumed_role_arn = (
        response.assumed_role_user.arn
        if response.assumed_role_user is not None
        else None
    )
    return AWSCredentialsIdentity(
        access_key_id=credentials.access_key_id,
        secret_access_key=credentials.secret_access_key,
        session_token=credentials.session_token,
        expiration=credentials.expiration,
        account_id=_account_id_from_arn(assumed_role_arn),
    )
