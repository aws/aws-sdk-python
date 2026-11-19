# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Temporary credentials, from JS v3 STS e2e."""

import pytest
from aws_sdk_sts.aio.client import AsyncSTSClient
from aws_sdk_sts.models import GetSessionTokenInput
from smithy_aws_core.identity import AWSCredentialsIdentity

from .conftest import STSFactory


@pytest.mark.skip(
    reason="TODO: GetSessionToken is denied (403) for role credentials, so this needs IAM user credentials"
)
async def test_session_token_credentials_keep_caller_identity(
    sts: AsyncSTSClient, make_sts: STSFactory
) -> None:
    """Verifies temporary credentials from GetSessionToken authenticate as the same account and user."""
    original = await sts.get_caller_identity()
    token = await sts.get_session_token(GetSessionTokenInput(duration_seconds=900))
    assert token.credentials is not None

    temporary = await make_sts(
        AWSCredentialsIdentity(
            access_key_id=token.credentials.access_key_id,
            secret_access_key=token.credentials.secret_access_key,
            session_token=token.credentials.session_token,
        )
    )
    session = await temporary.get_caller_identity()

    assert session.account == original.account
    assert session.arn == original.arn
    assert session.user_id == original.user_id
