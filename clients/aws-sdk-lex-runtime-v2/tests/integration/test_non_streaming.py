# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

import uuid

from aws_sdk_lex_runtime_v2.models import RecognizeTextOutput

from . import BOT_ALIAS_ID, LOCALE_ID, REGION, create_lex_client


async def test_recognize_text(lex_bot: str) -> None:
    """Test non-streaming RecognizeText operation."""
    async with await create_lex_client(REGION) as client:
        response = await client.recognize_text(
            bot_id=lex_bot,
            bot_alias_id=BOT_ALIAS_ID,
            locale_id=LOCALE_ID,
            session_id=str(uuid.uuid4()),
            text="Hello",
        )

        assert isinstance(response, RecognizeTextOutput)
        assert response.session_id is not None

        # Verify messages
        assert response.messages is not None
        assert len(response.messages) == 1
        msg = response.messages[0]
        assert msg.content_type == "PlainText"
        assert msg.content == "Hello! How can I help you?"

        # Verify session state
        assert response.session_state is not None
        assert response.session_state.intent is not None
        assert response.session_state.intent.name == "Greeting"
        assert response.session_state.intent.state == "Fulfilled"

        # Verify interpretations
        assert response.interpretations is not None
        assert len(response.interpretations) == 2
        interps_by_name = {
            i.intent.name: i for i in response.interpretations if i.intent
        }
        assert "Greeting" in interps_by_name
        assert "FallbackIntent" in interps_by_name
        assert interps_by_name["Greeting"].nlu_confidence is not None
        assert interps_by_name["Greeting"].nlu_confidence.score == 1.0
