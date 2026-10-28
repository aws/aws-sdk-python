# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
from datetime import datetime, timedelta

from smithy_core.exceptions import SmithyError


class IMDSConfigurationError(SmithyError):
    """Raised when IMDS credential configuration is invalid."""


class IMDSToken:
    """Represents an IMDSv2 session token."""

    def __init__(self, value: str, ttl: int):
        self._value = value
        self._ttl = ttl
        self._created_time = datetime.now()

    def is_expired(self) -> bool:
        return datetime.now() - self._created_time >= timedelta(seconds=self._ttl)

    @property
    def value(self) -> str:
        return self._value
