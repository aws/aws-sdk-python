# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_transcribe_streaming.aio.client import AsyncTranscribeStreamingClient
from aws_sdk_transcribe_streaming.aio.config import AsyncTranscribeStreamingConfig
from aws_sdk_transcribe_streaming.models import StartStreamTranscriptionInput
from smithy_test.aio import mock_async


async def test_should_set_streaming_headers() -> None:
    """The event stream request carries the event-stream content type and the streaming payload hash."""
    async with AsyncTranscribeStreamingClient(
        await AsyncTranscribeStreamingConfig.resolve(region="us-west-2")
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

            async with await client.start_stream_transcription(
                StartStreamTranscriptionInput(
                    media_sample_rate_hertz=144, media_encoding="ogg-opus"
                )
            ) as stream:
                await stream.input_stream.close()
                await stream.await_output()
