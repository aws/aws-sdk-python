# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""AssumeRole rules shared by the sync and async resolvers and providers."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
from typing import TYPE_CHECKING, Any, cast

from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain import StandardProvider
from smithy_core.exceptions import SmithyError, SmithyIdentityError

if TYPE_CHECKING:
    from aws_sdk_sts.models import AssumeRoleInput, AssumeRoleOutput

DEFAULT_STS_REGION = "us-east-1"

_ACCESS_KEY_ID = "aws_access_key_id"
_SECRET_ACCESS_KEY = "aws_secret_access_key"  # noqa: S105
_SESSION_TOKEN = "aws_session_token"  # noqa: S105
_ACCOUNT_ID = "aws_account_id"
_ROLE_ARN = "role_arn"
_ROLE_SESSION_NAME = "role_session_name"
_EXTERNAL_ID = "external_id"
_DURATION_SECONDS = "duration_seconds"
_SOURCE_PROFILE = "source_profile"
_CREDENTIAL_SOURCE = "credential_source"
_WEB_IDENTITY_TOKEN_FILE = "web_identity_token_file"
_REGION = "region"

_CREDENTIAL_SOURCE_SLOTS = {
    "Environment": StandardProvider.ENVIRONMENT,
    "EcsContainer": StandardProvider.ECS_CONTAINER,
    "Ec2InstanceMetadata": StandardProvider.EC2_INSTANCE_METADATA,
}


class AssumeRoleConfigurationError(SmithyError):
    """Raised when AssumeRole credential configuration is invalid."""


@dataclass(frozen=True, kw_only=True)
class StaticSource:
    identity: AWSCredentialsIdentity


@dataclass(frozen=True, kw_only=True)
class CredentialSource:
    name: str
    slot: StandardProvider


@dataclass(frozen=True, kw_only=True)
class AssumeRolePlan:
    role_arn: str
    role_session_name: str | None
    external_id: str | None
    duration_seconds: int | None
    source: StaticSource | CredentialSource | AssumeRolePlan


def is_assume_role_profile(
    config_file: MergedConfig | None, profile_name: str | None
) -> bool:
    """Return whether the profile is configured for AssumeRole.

    A profile with a role ARN and a web identity token file, but no source, is
    configured for web identity instead.
    """
    if profile_name is None or config_file is None:
        return False
    if config_file.get(profile_name, _ROLE_ARN) is None:
        return False
    return (
        config_file.get(profile_name, _SOURCE_PROFILE) is not None
        or config_file.get(profile_name, _CREDENTIAL_SOURCE) is not None
        or not config_file.get(profile_name, _WEB_IDENTITY_TOKEN_FILE)
    )


def default_session_name() -> str:
    return f"aws-sdk-python-{uuid.uuid4().hex[:16]}"


def resolve_sts_region(
    *,
    config_file: MergedConfig | None = None,
    profile_name: str | None = None,
) -> str:
    profile_region = (
        config_file.get(profile_name, _REGION)
        if config_file is not None and profile_name is not None
        else None
    )
    return (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or profile_region
        or DEFAULT_STS_REGION
    )


def validate_profile(config_file: MergedConfig, profile_name: str) -> None:
    if config_file.get_profile(profile_name) is None:
        raise AssumeRoleConfigurationError(f"Profile '{profile_name}' does not exist.")


def plan_profile(config_file: MergedConfig, profile_name: str) -> AssumeRolePlan:
    """Walk a profile's role chain into a plan, validating every step."""
    return _plan_assume_role(config_file, profile_name, (profile_name,))


def find_provider(group: str, slot: StandardProvider) -> Any | None:
    """Load the chain provider installed for a standard slot."""
    for entry_point in metadata.entry_points(group=group):
        if entry_point.name == slot.canonical_name:
            return cast(Callable[[], Any], entry_point.load())()
    return None


def require_provider(provider: Any | None, source: CredentialSource) -> Any:
    if provider is None:
        raise AssumeRoleConfigurationError(
            f"No provider is installed for credential source '{source.name}'. "
            f"Install '{source.slot.module_suggestion}'."
        )
    return provider


def first_resolver(resolvers: tuple[Any, ...], source: CredentialSource) -> Any:
    if not resolvers:
        raise AssumeRoleConfigurationError(
            f"'{source.name}' credential source is not configured."
        )
    return resolvers[0]


def assume_role_input(
    *,
    role_arn: str,
    role_session_name: str,
    external_id: str | None,
    duration_seconds: int | None,
) -> AssumeRoleInput:
    from aws_sdk_sts.models import AssumeRoleInput

    return AssumeRoleInput(
        role_arn=role_arn,
        role_session_name=role_session_name,
        external_id=external_id,
        duration_seconds=duration_seconds,
    )


def identity_from_response(response: AssumeRoleOutput) -> AWSCredentialsIdentity:
    credentials = response.credentials
    if credentials is None:
        raise SmithyIdentityError(
            "STS AssumeRole response did not contain credentials."
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


def _plan_assume_role(
    config_file: MergedConfig, profile_name: str, visited: tuple[str, ...]
) -> AssumeRolePlan:
    role_arn = config_file.get(profile_name, _ROLE_ARN)
    if role_arn is None:
        raise AssumeRoleConfigurationError(
            f"Profile '{profile_name}' does not define role_arn."
        )

    source_profile = config_file.get(profile_name, _SOURCE_PROFILE)
    credential_source = config_file.get(profile_name, _CREDENTIAL_SOURCE)
    if source_profile is not None and credential_source is not None:
        raise AssumeRoleConfigurationError(
            f"Profile '{profile_name}' cannot define both 'source_profile' and 'credential_source'."
        )
    if source_profile is not None:
        source = _plan_source_profile(config_file, source_profile, visited)
    elif credential_source is not None:
        source = _plan_credential_source(credential_source)
    else:
        raise AssumeRoleConfigurationError(
            f"Profile '{profile_name}' must define either 'source_profile' or 'credential_source'."
        )

    return AssumeRolePlan(
        role_arn=role_arn,
        role_session_name=config_file.get(profile_name, _ROLE_SESSION_NAME),
        external_id=config_file.get(profile_name, _EXTERNAL_ID),
        duration_seconds=_parse_duration_seconds(config_file, profile_name),
        source=source,
    )


def _plan_source_profile(
    config_file: MergedConfig, source_profile_name: str, visited: tuple[str, ...]
) -> StaticSource | AssumeRolePlan:
    is_direct_self_reference = len(visited) > 0 and source_profile_name == visited[-1]
    if source_profile_name in visited and not is_direct_self_reference:
        path = " -> ".join((*visited, source_profile_name))
        raise AssumeRoleConfigurationError(
            f"Circular source_profile reference: {path}."
        )

    if config_file.get_profile(source_profile_name) is None:
        raise AssumeRoleConfigurationError(
            f"Source profile '{source_profile_name}' does not exist."
        )

    if any(
        config_file.get(source_profile_name, key) is not None
        for key in (_ACCESS_KEY_ID, _SECRET_ACCESS_KEY, _SESSION_TOKEN)
    ):
        return _plan_static(config_file, source_profile_name)

    if is_direct_self_reference:
        raise AssumeRoleConfigurationError(
            f"Self-referencing profile '{source_profile_name}' must contain "
            "complete static credentials."
        )

    if is_assume_role_profile(config_file, source_profile_name):
        return _plan_assume_role(
            config_file, source_profile_name, (*visited, source_profile_name)
        )

    raise AssumeRoleConfigurationError(
        f"Source profile '{source_profile_name}' has no supported credential source."
    )


def _plan_static(config_file: MergedConfig, profile_name: str) -> StaticSource:
    access_key_id = config_file.get(profile_name, _ACCESS_KEY_ID)
    secret_access_key = config_file.get(profile_name, _SECRET_ACCESS_KEY)
    if access_key_id is None or secret_access_key is None:
        raise AssumeRoleConfigurationError(
            f"Profile '{profile_name}' contains partial credentials."
        )
    return StaticSource(
        identity=AWSCredentialsIdentity(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=config_file.get(profile_name, _SESSION_TOKEN),
            account_id=config_file.get(profile_name, _ACCOUNT_ID),
        )
    )


def _plan_credential_source(credential_source: str) -> CredentialSource:
    slot = _CREDENTIAL_SOURCE_SLOTS.get(credential_source)
    if slot is None:
        raise AssumeRoleConfigurationError(
            f"Unsupported 'credential_source': '{credential_source}'."
        )
    return CredentialSource(name=credential_source, slot=slot)


def _parse_duration_seconds(config_file: MergedConfig, profile_name: str) -> int | None:
    duration_seconds = config_file.get(profile_name, _DURATION_SECONDS)
    if duration_seconds is None:
        return None
    try:
        return int(duration_seconds)
    except ValueError:
        return None


def _account_id_from_arn(arn: str | None) -> str | None:
    if arn is None:
        return None
    parts = arn.split(":")
    return parts[4] if len(parts) >= 5 and parts[4] else None
