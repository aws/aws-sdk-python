# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
__version__ = "0.4.0"

from .providers import EcsContainerProvider
from .resolvers import ContainerCredentialsResolver

__all__ = (
    "ContainerCredentialsResolver",
    "EcsContainerProvider",
)
