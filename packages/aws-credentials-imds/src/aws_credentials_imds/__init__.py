# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
__version__ = "0.4.0"

from .client import IMDSConfig, IMDSConfigurationError
from .providers import Ec2InstanceMetadataProvider
from .resolvers import IMDSCredentialsResolver

__all__ = (
    "Ec2InstanceMetadataProvider",
    "IMDSConfig",
    "IMDSConfigurationError",
    "IMDSCredentialsResolver",
)
