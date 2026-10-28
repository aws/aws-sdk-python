# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import json
from datetime import UTC, datetime

from smithy_aws_core.identity import AWSCredentialsIdentity, AWSIdentityProperties
from smithy_core.aio.interfaces.identity import AsyncIdentityResolver
from smithy_core.exceptions import SmithyIdentityError
from smithy_http.aio.aiohttp import AIOHTTPClient
from smithy_http.aio.interfaces import AsyncHTTPClient

from .client import IMDSClient, IMDSConfig


class IMDSCredentialsResolver(
    AsyncIdentityResolver[AWSCredentialsIdentity, AWSIdentityProperties]
):
    """Resolves AWS credentials from the EC2 Instance Metadata Service."""

    _METADATA_PATH_BASE = "/latest/meta-data/iam/security-credentials"

    def __init__(
        self,
        http_client: AsyncHTTPClient | None = None,
        config: IMDSConfig | None = None,
    ):
        self._http_client = http_client or AIOHTTPClient()
        self._imds_client = IMDSClient(http_client=self._http_client, config=config)
        self._config = config or IMDSConfig()
        self._credentials = None

    async def get_identity(
        self, *, properties: AWSIdentityProperties
    ) -> AWSCredentialsIdentity:
        """Return cached credentials if valid, otherwise fetch from IMDS."""
        if (
            self._credentials is not None
            and self._credentials.expiration
            and datetime.now(UTC) < self._credentials.expiration
        ):
            return self._credentials

        profile = self._config.ec2_instance_profile_name
        if profile is None:
            profile = await self._imds_client.get(path=self._METADATA_PATH_BASE)

        creds_str = await self._imds_client.get(
            path=f"{self._METADATA_PATH_BASE}/{profile}"
        )
        creds = json.loads(creds_str)

        access_key_id = creds.get("AccessKeyId")
        secret_access_key = creds.get("SecretAccessKey")
        session_token = creds.get("Token")
        account_id = creds.get("AccountId")
        expiration = creds.get("Expiration")
        if expiration is not None:
            expiration = datetime.fromisoformat(expiration).replace(tzinfo=UTC)

        if access_key_id is None or secret_access_key is None:
            raise SmithyIdentityError("AccessKeyId and SecretAccessKey are required")

        self._credentials = AWSCredentialsIdentity(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            expiration=expiration,
            account_id=account_id,
        )
        return self._credentials
