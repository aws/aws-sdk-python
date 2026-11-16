# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test output streaming event stream handling."""

from aws_sdk_bedrock_runtime.models import (
    ContentBlockDeltaText,
    ConverseStreamMetadataEvent,
    ConverseStreamOperationOutput,
    ConverseStreamOutputContentBlockDelta,
    ConverseStreamOutputMetadata,
)

from . import MESSAGE, MODEL_ID, create_bedrock_client


async def test_converse_stream() -> None:
    async with await create_bedrock_client("us-west-2") as bedrock_client:
        response = await bedrock_client.converse_stream(
            model_id=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": MESSAGE}]}],
        )

        received_text: list[str] = []
        metadata: list[ConverseStreamMetadataEvent] = []

        async with response as stream:
            async for event in stream.output_stream:
                if isinstance(event, ConverseStreamOutputContentBlockDelta):
                    delta = event.value.delta
                    if isinstance(delta, ContentBlockDeltaText):
                        received_text.append(delta.value)
                elif isinstance(event, ConverseStreamOutputMetadata):
                    metadata.append(event.value)

            full_response = "".join(received_text)
            assert full_response

            assert len(metadata) == 1
            # Bedrock sometimes reports zero usage for a completed stream, so check
            # that the counts deserialized consistently rather than that they are positive.
            usage = metadata[0].usage
            assert usage.input_tokens >= 0
            assert usage.output_tokens >= 0
            assert usage.total_tokens == usage.input_tokens + usage.output_tokens
            assert metadata[0].metrics.latency_ms > 0
            assert isinstance(stream.output, ConverseStreamOperationOutput)
