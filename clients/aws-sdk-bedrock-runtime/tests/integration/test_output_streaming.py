# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test output streaming event stream handling."""

from aws_sdk_bedrock_runtime.models import (
    ContentBlockDeltaText,
    ContentBlockText,
    ConverseStreamOperationOutput,
    ConverseStreamOutputContentBlockDelta,
    ConverseStreamOutputMetadata,
    Message,
)

from . import MESSAGE, MODEL_ID, create_bedrock_client


async def test_converse_stream() -> None:
    async with await create_bedrock_client("us-west-2") as bedrock_client:
        input_message = Message(role="user", content=[ContentBlockText(value=MESSAGE)])
        response = await bedrock_client.converse_stream(
            model_id=MODEL_ID, messages=[input_message]
        )

        received_text: list[str] = []
        metadata_received = False

        async with response as stream:
            async for event in stream.output_stream:
                if isinstance(event, ConverseStreamOutputContentBlockDelta):
                    delta = event.value.delta
                    if isinstance(delta, ContentBlockDeltaText):
                        received_text.append(delta.value)
                elif isinstance(event, ConverseStreamOutputMetadata):
                    metadata_received = True
                    assert event.value.usage.input_tokens > 0
                    assert event.value.usage.output_tokens > 0

            full_response = "".join(received_text)
            assert full_response

            assert metadata_received
            assert isinstance(stream.output, ConverseStreamOperationOutput)
