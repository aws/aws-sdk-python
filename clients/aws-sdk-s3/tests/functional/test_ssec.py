# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import base64
import hashlib

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import CopyObjectInput, PutObjectInput
from smithy_test import mock


# TODO: base64-encode SSE-C keys and send their MD5 digests
@pytest.mark.skip
def test_adds_hash_for_sse_customer_key_and_copy_source_sse_customer_key() -> None:
    """CopyObject sends base64 SSE-C keys and their MD5 digests for the source and target."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="PUT",
        scheme="https",
        hostname="s3.us-west-2.amazonaws.com",
        path="/b/k",
        query={"x-id": "CopyObject"},
        headers={
            "x-amz-copy-source": "s",
            "x-amz-server-side-encryption-customer-key": "c3NlLWN1c3RvbWVyLWtleQ==",
            "x-amz-server-side-encryption-customer-key-md5": "E+/nTVpQe9+cNzOKBFXSlA==",
            "x-amz-copy-source-server-side-encryption-customer-key": "Y29weS1zb3VyY2Utc3NlLWN1c3RvbWVyLWtleQ==",
            "x-amz-copy-source-server-side-encryption-customer-key-md5": "4CgOx9iMMPvAQi7bWXEJEw==",
        },
    )

    client.copy_object(
        CopyObjectInput(
            sse_customer_key="sse-customer-key",
            copy_source_sse_customer_key="copy-source-sse-customer-key",
            bucket="b",
            copy_source="s",
            key="k",
        )
    )


# TODO: send SSE-C key MD5 digests, and send a checksum header for bodies of known length
@pytest.mark.skip
def test_verifies_headers_for_put_object_with_base64_encoded_sse_customer_key() -> None:
    """PutObject with a base64 SSE-C key sends the key and its MD5 digest."""
    client = S3Client(S3Config.resolve(region="us-east-1"))
    mock(client).expect_request(
        method="PUT",
        scheme="https",
        hostname="testbucket.s3.us-east-1.amazonaws.com",
        path="/foo",
        query={"x-id": "PutObject"},
        headers={
            "x-amz-server-side-encryption-customer-algorithm": "AES256",
            "x-amz-server-side-encryption-customer-key": "UNhY4JhezH9gQYqvDMWrWH9CwlcKiECVqejMrND2VFw=",
            "x-amz-server-side-encryption-customer-key-md5": "SwoBWUcJBbc/WRhR6hZGCA==",
            "content-length": "14",
        },
        body="This is a test",
    )
    example_key = hashlib.sha256(b"example").digest()

    client.put_object(
        PutObjectInput(
            bucket="testbucket",
            body=b"This is a test",
            key="foo",
            sse_customer_key=base64.b64encode(example_key).decode(),
            sse_customer_algorithm="AES256",
        )
    )
