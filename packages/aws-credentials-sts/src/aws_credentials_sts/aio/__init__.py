# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from .providers import ProfileAssumeRoleProvider
from .resolvers import (
    AssumeRoleCredentialsResolver,
    ProfileAssumeRoleCredentialsResolver,
)

__all__ = (
    "AssumeRoleCredentialsResolver",
    "ProfileAssumeRoleCredentialsResolver",
    "ProfileAssumeRoleProvider",
)
