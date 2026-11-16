# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
from base64 import b64encode
from io import BytesIO

from aws_sdk_bedrock_runtime.aio.client import AsyncBedrockRuntimeClient
from aws_sdk_bedrock_runtime.aio.config import AsyncBedrockRuntimeConfig
from aws_sdk_bedrock_runtime.models import (
    BidirectionalInputPayloadPart,
    BidirectionalOutputPayloadPart,
    InvokeModelWithBidirectionalStreamInputChunk,
    InvokeModelWithBidirectionalStreamOperationInput,
    InvokeModelWithBidirectionalStreamOutputChunk,
)
from smithy_aws_event_stream.events import Event, EventMessage
from smithy_test.aio import mock_async

SERVER_CHUNK = bytes([48, 49, 50, 51, 52, 56, 57, 57, 57])


async def test_should_send_input_stream_chunks_as_signed_event_frames() -> None:
    """Chunks sent on the input stream go out as signed event frames, and response frames come back as output chunks."""
    server_event = EventMessage(
        headers={
            ":event-type": "chunk",
            ":content-type": "application/json",
            ":message-type": "event",
        },
        payload=json.dumps({"bytes": b64encode(SERVER_CHUNK).decode()}).encode(),
    ).encode()

    async with AsyncBedrockRuntimeClient(
        await AsyncBedrockRuntimeConfig.resolve(
            region="us-west-2", aws_access_key_id="INTEG", aws_secret_access_key="INTEG"
        )
    ) as client:
        async with await mock_async(client) as controller:
            controller.expect_request().respond_with(
                headers={"content-type": "application/vnd.amazon.eventstream"},
                body=server_event * 10,
            )

            async with await client.invoke_model_with_bidirectional_stream(
                InvokeModelWithBidirectionalStreamOperationInput(model_id="bedrock")
            ) as stream:
                for chunk in ([0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]):
                    await stream.input_stream.send(
                        InvokeModelWithBidirectionalStreamInputChunk(
                            value=BidirectionalInputPayloadPart(bytes_=bytes(chunk))
                        )
                    )
                await stream.input_stream.close()
                _, output_stream = await stream.await_output()
                response_chunks = [event async for event in output_stream]

    assert (
        response_chunks
        == [
            InvokeModelWithBidirectionalStreamOutputChunk(
                value=BidirectionalOutputPayloadPart(bytes_=SERVER_CHUNK)
            )
        ]
        * 10
    )

    request_body = controller.requests[0].body
    assert isinstance(request_body, bytes)
    source = BytesIO(request_body)
    signed_events: list[Event] = []
    while (event := Event.decode(source)) is not None:
        signed_events.append(event)
    sent_bodies: list[object] = []
    for signed in signed_events:
        assert isinstance(signed.message.headers[":date"], datetime.datetime)
        assert isinstance(signed.message.headers[":chunk-signature"], bytes)
        inner = Event.decode(BytesIO(signed.message.payload))
        if inner is not None:
            sent_bodies.append(json.loads(inner.message.payload))
    assert sent_bodies == [
        {"bytes": b64encode(bytes([0, 1, 2, 3])).decode()},
        {"bytes": b64encode(bytes([4, 5, 6, 7])).decode()},
        {"bytes": b64encode(bytes([8, 9, 10, 11])).decode()},
    ]
