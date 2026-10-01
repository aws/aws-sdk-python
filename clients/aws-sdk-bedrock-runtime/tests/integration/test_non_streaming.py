# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test non-streaming output type handling."""

from aws_sdk_bedrock_runtime.models import (
    ContentBlockText,
    ConverseOperationOutput,
    ConverseOutputMessage,
    Message,
)

from . import MESSAGE, MODEL_ID, create_bedrock_client


async def test_converse() -> None:
    async with await create_bedrock_client("us-west-2") as bedrock_client:
        input_message = Message(role="user", content=[ContentBlockText(value=MESSAGE)])
        response = await bedrock_client.converse(
            model_id=MODEL_ID, messages=[input_message]
        )

        assert isinstance(response, ConverseOperationOutput)
        assert isinstance(response.output, ConverseOutputMessage)

        output_message = response.output.value
        assert output_message.role == "assistant"
        assert len(output_message.content) > 0

        content_block = output_message.content[0]
        assert isinstance(content_block, ContentBlockText)
        assert isinstance(content_block.value, str) and content_block.value

        assert response.usage.input_tokens > 0
        assert response.usage.output_tokens > 0
