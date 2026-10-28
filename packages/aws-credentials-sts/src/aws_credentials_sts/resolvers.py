# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import os

from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity.chain import StandardProvider
from smithy_core.exceptions import SmithyError

_DEFAULT_STS_REGION = "us-east-1"

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
_REGION = "region"

_CREDENTIAL_SOURCE_SLOTS = {
    "Environment": StandardProvider.ENVIRONMENT,
    "EcsContainer": StandardProvider.ECS_CONTAINER,
    "Ec2InstanceMetadata": StandardProvider.EC2_INSTANCE_METADATA,
}


class AssumeRoleConfigurationError(SmithyError):
    """Raised when AssumeRole credential configuration is invalid."""


def _account_id_from_arn(arn: str | None) -> str | None:
    if arn is None:
        return None
    parts = arn.split(":")
    return parts[4] if len(parts) >= 5 and parts[4] else None


def _resolve_sts_region(
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
        or _DEFAULT_STS_REGION
    )
