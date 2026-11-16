# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_lex_runtime_v2.aio.client import AsyncLexRuntimeV2Client
from aws_sdk_lex_runtime_v2.aio.config import AsyncLexRuntimeV2Config
from aws_sdk_lex_runtime_v2.models import StartConversationInput
from smithy_test.aio import mock_async


async def test_should_set_streaming_headers() -> None:
    """The event stream request carries the event-stream content type and the streaming payload hash."""
    async with AsyncLexRuntimeV2Client(
        await AsyncLexRuntimeV2Config.resolve(region="us-west-2")
    ) as client:
        async with await mock_async(client) as controller:
            controller.expect_request(
                headers={
                    "content-type": "application/vnd.amazon.eventstream",
                    "x-amz-content-sha256": "STREAMING-AWS4-HMAC-SHA256-EVENTS",
                }
            ).respond_with(
                headers={"content-type": "application/vnd.amazon.eventstream"}
            )

            async with await client.start_conversation(
                StartConversationInput(
                    bot_id="undefined",
                    bot_alias_id="undefined",
                    locale_id="undefined",
                    session_id="undefined",
                )
            ) as stream:
                await stream.input_stream.close()
                await stream.await_output()
