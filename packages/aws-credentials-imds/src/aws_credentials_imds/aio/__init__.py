# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from .client import IMDSConfig
from .providers import Ec2InstanceMetadataProvider
from .resolvers import IMDSCredentialsResolver

__all__ = (
    "Ec2InstanceMetadataProvider",
    "IMDSConfig",
    "IMDSCredentialsResolver",
)
