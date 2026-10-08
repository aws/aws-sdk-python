# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
__version__ = "0.4.0"

from .providers import ProfileAssumeRoleProvider
from .resolvers import (
    AssumeRoleConfigurationError,
    AssumeRoleCredentialsResolver,
    ProfileAssumeRoleCredentialsResolver,
)

__all__ = (
    "AssumeRoleConfigurationError",
    "AssumeRoleCredentialsResolver",
    "ProfileAssumeRoleCredentialsResolver",
    "ProfileAssumeRoleProvider",
)
