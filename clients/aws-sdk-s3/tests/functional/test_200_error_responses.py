# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import (
    CompletedMultipartUpload,
    CompleteMultipartUploadInput,
    CopyObjectInput,
)
from smithy_core.retries import RetryStrategyOptions
from smithy_test import mock

XML_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>InternalError</Code>
    <Message>We encountered an internal error. Please try again.</Message>
    <RequestId>EXAMPLE</RequestId>
</Error>"""

COPY_OBJECT_RESULT = """<?xml version="1.0" encoding="UTF-8"?>
<CopyObjectResult>
  <ETag>&quot;etag&quot;</ETag>
  <LastModified>2026-01-01T00:00:00.000Z</LastModified>
</CopyObjectResult>"""


# TODO: treat 200 responses with an Error body as errors
@pytest.mark.skip
def test_should_retry_on_copy_object_200_with_error_xml_body() -> None:
    """A CopyObject 200 response with an Error body counts as a failure and triggers a retry."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(hostname="/./").times(3).respond_with(
            body=XML_ERROR
        ).respond_with(body=XML_ERROR).respond_with(body=COPY_OBJECT_RESULT)

        result = client.copy_object(
            CopyObjectInput(
                bucket="bucket", key="key", copy_source="src-bucket/src-key"
            )
        )

    assert result.copy_object_result is not None
    assert result.copy_object_result.e_tag == '"etag"'


# TODO: treat 200 responses with an Error body as errors
@pytest.mark.skip
def test_should_retry_on_complete_multipart_upload_200_with_error_xml_body() -> None:
    """A CompleteMultipartUpload 200 response with an Error body counts as a failure and triggers a retry."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(hostname="/./").times(3).respond_with(
            body=XML_ERROR
        ).respond_with(body=XML_ERROR).respond_with(
            body="""<?xml version="1.0" encoding="UTF-8"?>
<CompleteMultipartUploadResult>
   <Location>string</Location>
   <Bucket>string</Bucket>
   <Key>string</Key>
   <ETag>string</ETag>
   <ChecksumCRC32>string</ChecksumCRC32>
   <ChecksumCRC32C>string</ChecksumCRC32C>
   <ChecksumCRC64NVME>string</ChecksumCRC64NVME>
   <ChecksumSHA1>string</ChecksumSHA1>
   <ChecksumSHA256>string</ChecksumSHA256>
   <ChecksumType>string</ChecksumType>
</CompleteMultipartUploadResult>"""
        )

        result = client.complete_multipart_upload(
            CompleteMultipartUploadInput(
                bucket="bucket",
                key="key",
                upload_id="upload-id",
                multipart_upload=CompletedMultipartUpload(parts=[]),
            )
        )

    assert result.e_tag == "string"


def test_should_not_raise_on_copy_object_200_with_success_xml_body() -> None:
    """A CopyObject 200 response with a success body parses as output."""
    client = S3Client(
        S3Config.resolve(
            region="us-west-2", retry_strategy=RetryStrategyOptions(max_attempts=1)
        )
    )
    mock(client).expect_request(hostname="/./").respond_with(body=COPY_OBJECT_RESULT)

    result = client.copy_object(
        CopyObjectInput(bucket="bucket", key="key", copy_source="src-bucket/src-key")
    )

    assert result.response_metadata.http_status_code == 200
