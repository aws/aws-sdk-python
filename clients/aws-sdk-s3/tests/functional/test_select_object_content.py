# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.aio.config import AsyncS3Config
from aws_sdk_s3.models import (
    CSVInput,
    CSVOutput,
    EndEvent,
    InputSerialization,
    OutputSerialization,
    SelectObjectContentEventStreamEnd,
    SelectObjectContentInput,
)
from smithy_test.aio import mock_async

# See https://docs.aws.amazon.com/AmazonS3/latest/API/RESTSelectObjectAppendix.html
END_EVENT = bytes(
    [
        # message size
        *[0, 0, 0, 97],
        # header size
        *[0, 0, 0, 81],
        # prelude crc
        *[221, 28, 224, 246],
        # :event-type
        11,
        *[58, 101, 118, 101, 110, 116, 45, 116, 121, 112, 101],
        7,
        # End
        0,
        3,
        *[69, 110, 100],
        # :content-type
        13,
        *[58, 99, 111, 110, 116, 101, 110, 116, 45, 116, 121, 112, 101],
        7,
        # application/octet-stream
        0,
        24,
        *[97, 112, 112, 108, 105, 99, 97, 116, 105, 111, 110, 47, 111, 99, 116, 101],
        *[116, 45, 115, 116, 114, 101, 97, 109],
        # :message-type
        13,
        *[58, 109, 101, 115, 115, 97, 103, 101, 45, 116, 121, 112, 101],
        7,
        # event
        0,
        5,
        *[101, 118, 101, 110, 116],
        # message crc
        *[75, 107, 103, 102],
    ]
)


async def test_should_send_select_request_and_read_events() -> None:
    """SelectObjectContent sends the SQL request body and yields the events of the response stream."""

    def has_select_parameters(body: bytes) -> None:
        assert (
            b"<Expression>SELECT user_name FROM S3Object WHERE cast(age as int) &gt; 20</Expression>"
            in body
        )
        assert b"<ExpressionType>SQL</ExpressionType>" in body

    async with AsyncS3Client(await AsyncS3Config.resolve(region="us-west-2")) as client:
        async with await mock_async(client) as controller:
            controller.expect_request(
                hostname=r"/test-bucket\.s3\.us-west-2\.amazonaws\.com/",
                method="POST",
                path="/test-key",
                headers={
                    "authorization": "/AWS4-HMAC-SHA256 Credential/",
                    "content-type": "application/xml",
                    "x-amz-content-sha256": "/./",
                },
                body=has_select_parameters,
            ).respond_with(
                headers={"x-amz-checksum-crc32": "3117266289"}, body=END_EVENT
            )

            async with await client.select_object_content(
                SelectObjectContentInput(
                    bucket="test-bucket",
                    key="test-key",
                    expression_type="SQL",
                    expression="SELECT user_name FROM S3Object WHERE cast(age as int) > 20",
                    input_serialization=InputSerialization(
                        csv=CSVInput(
                            file_header_info="USE",
                            record_delimiter="\n",
                            field_delimiter=",",
                        )
                    ),
                    output_serialization=OutputSerialization(csv=CSVOutput()),
                )
            ) as stream:
                events = [event async for event in stream.output_stream]

    assert stream.output.response_metadata.http_status_code == 200
    assert stream.output_stream is not None
    assert events == [SelectObjectContentEventStreamEnd(value=EndEvent())]
