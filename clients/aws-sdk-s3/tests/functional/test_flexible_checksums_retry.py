# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import PutObjectInput
from smithy_core.exceptions import CallError
from smithy_test import mock


# TODO: retry 500 responses without a modeled error
@pytest.mark.skip
def test_retry_reuses_the_checksum() -> None:
    """Retried attempts send the checksum computed for the first attempt."""
    max_attempts = 3
    client = S3Client(S3Config.resolve(region="us-west-2", max_attempts=max_attempts))
    controller = mock(client)
    controller.expect_request(method="PUT").times(max_attempts).respond_with(
        status_code=500
    )

    with pytest.raises(CallError):
        client.put_object(PutObjectInput(bucket="b", key="k", body=b"hello"))

    assert len(controller.requests) == max_attempts
    checksums = [
        request.fields["x-amz-checksum-crc32"].as_string()
        if "x-amz-checksum-crc32" in request.fields
        else request.body
        for request in controller.requests
    ]
    assert checksums[0]
    assert checksums == [checksums[0]] * max_attempts
