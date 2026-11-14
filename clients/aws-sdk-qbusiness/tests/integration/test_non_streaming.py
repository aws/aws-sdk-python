# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

import uuid

from aws_sdk_qbusiness.models import ChatSyncOutput

from . import REGION, create_qbusiness_client


async def test_chat_sync(qbusiness_app: str) -> None:
    """Test non-streaming ChatSync operation."""
    async with await create_qbusiness_client(REGION) as qbusiness_client:
        response = await qbusiness_client.chat_sync(
            application_id=qbusiness_app,
            user_message="Hello",
            client_token=str(uuid.uuid4()),
        )

        assert isinstance(response, ChatSyncOutput)
        assert response.conversation_id is not None
        assert response.system_message is not None
        assert isinstance(response.system_message, str)
        assert len(response.system_message) > 0
        assert response.system_message_id is not None
        assert response.user_message_id is not None
        assert response.source_attributions is not None
        assert response.failed_attachments is not None
