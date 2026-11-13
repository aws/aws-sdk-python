# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import base64

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import GetObjectInput, PutObjectInput
from smithy_aws_core.checksums import ChecksumStream, UnsupportedChecksumAlgorithmError
from smithy_aws_core.config.types import (
    RequestChecksumCalculation,
    ResponseChecksumValidation,
)
from smithy_core.utils import read_streaming_blob
from smithy_test import mock

DEFAULT_CHECKSUM_ALGORITHM = "CRC32"

TEST_CASES: list[tuple[str, str | None, str]] = [
    ("", "CRC32", "AAAAAA=="),
    ("abc", "CRC32", "NSRBwg=="),
    ("Hello world", "CRC32", "i9aeUg=="),
    ("", "CRC32C", "AAAAAA=="),
    ("abc", "CRC32C", "Nks/tw=="),
    ("Hello world", "CRC32C", "crUfeA=="),
    ("", "CRC64NVME", "AAAAAAAAAAA="),
    ("abc", "CRC64NVME", "BeXKuz/B+us="),
    ("Hello world", "CRC64NVME", "OOJZ0D8xKts="),
    ("", "SHA1", "2jmj7l5rSw0yVb/vlWAYkK/YBwk="),
    ("abc", "SHA1", "qZk+NkcGgWq6PiVxeFDCbJzQ2J0="),
    ("Hello world", "SHA1", "e1AsOh9IyGCa4hLN+2Od7jlnP14="),
    ("", "SHA256", "47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU="),
    ("abc", "SHA256", "ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0="),
    ("Hello world", "SHA256", "ZOyIygCyaOW6GjVnihtTFtIS9PNmskdyMlNKiuyjfzw="),
    ("", None, "AAAAAA=="),
    ("abc", None, "NSRBwg=="),
    ("Hello world", None, "i9aeUg=="),
]

CASE_IDS = [f"{algorithm}-{body!r}" for body, algorithm, _ in TEST_CASES]

SETTINGS: list[RequestChecksumCalculation | None] = [
    None,
    "when_supported",
    "when_required",
]

VALIDATION_SETTINGS: list[ResponseChecksumValidation | None] = [
    None,
    "when_supported",
    "when_required",
]

HELLO_WORLD_2 = base64.b64encode(b"Hello, world.2").decode()


# TODO: send a checksum header for bodies of known length in place of an aws-chunked trailer, and decide on the CRC32 default
@pytest.mark.skip
@pytest.mark.parametrize("request_checksum_calculation", SETTINGS)
@pytest.mark.parametrize(
    ("body", "checksum_algorithm", "checksum_value"), TEST_CASES, ids=CASE_IDS
)
def test_should_send_checksum_on_put_object(
    request_checksum_calculation: RequestChecksumCalculation | None,
    body: str,
    checksum_algorithm: str | None,
    checksum_value: str,
) -> None:
    """PutObject sends the expected checksum header for each body, algorithm and calculation setting."""
    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            request_checksum_calculation=request_checksum_calculation,
        )
    )
    checksum_header = (
        f"x-amz-checksum-{(checksum_algorithm or DEFAULT_CHECKSUM_ALGORITHM).lower()}"
    )
    headers: dict[str, str] = {
        "content-type": "application/octet-stream",
        "user-agent": "/./",
        "x-amz-date": "/./",
        "x-amz-content-sha256": "/./",
        "authorization": "/./",
    }
    if body:
        headers["content-length"] = str(len(body))
    if not (
        request_checksum_calculation == "when_required" and checksum_algorithm is None
    ):
        headers[checksum_header] = checksum_value
        if checksum_algorithm is not None:
            headers["x-amz-sdk-checksum-algorithm"] = checksum_algorithm
    with mock(client) as controller:
        controller.expect_request(
            method="PUT",
            scheme="https",
            hostname="s3.us-west-2.amazonaws.com",
            path="/b/k",
            headers=headers,
            query={"x-id": "PutObject"},
        )

        client.put_object(
            PutObjectInput(
                bucket="b",
                key="k",
                body=body.encode(),
                checksum_algorithm=checksum_algorithm,
            )
        )


@pytest.mark.parametrize("response_checksum_validation", VALIDATION_SETTINGS)
@pytest.mark.parametrize(
    ("body", "checksum_algorithm", "checksum_value"), TEST_CASES, ids=CASE_IDS
)
def test_should_validate_checksum_on_get_object(
    response_checksum_validation: ResponseChecksumValidation | None,
    body: str,
    checksum_algorithm: str | None,
    checksum_value: str,
) -> None:
    """GetObject requests checksum mode and returns the body for each algorithm and validation setting."""
    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            response_checksum_validation=response_checksum_validation,
        )
    )
    checksum_header = (
        f"x-amz-checksum-{(checksum_algorithm or DEFAULT_CHECKSUM_ALGORITHM).lower()}"
    )
    headers: dict[str, str] = {
        "user-agent": "/./",
        "x-amz-date": "/./",
        "x-amz-content-sha256": "/./",
        "authorization": "/./",
    }
    if not (response_checksum_validation == "when_required" and not checksum_algorithm):
        headers["x-amz-checksum-mode"] = "ENABLED"
    mock(client).expect_request(
        method="GET",
        scheme="https",
        hostname="s3.us-west-2.amazonaws.com",
        path="/b/k",
        headers=headers,
        query={"x-id": "GetObject"},
    ).respond_with(
        headers={
            "content-type": "application/octet-stream",
            "content-length": str(len(body)),
            checksum_header: checksum_value,
        },
        body=body.encode(),
    )

    output = client.get_object(
        GetObjectInput(
            bucket="b",
            key="k",
            # The SDK sets checksum_mode itself when no algorithm is given.
            checksum_mode="ENABLED" if checksum_algorithm else None,
        )
    )

    assert read_streaming_blob(output.body) == body.encode()


# TODO: send a trailing checksum for bodies of unknown length
@pytest.mark.skip
def test_should_not_set_binary_file_content_length() -> None:
    """A body of unknown length goes out without a content-length."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            method="PUT",
            scheme="https",
            hostname="s3.us-west-2.amazonaws.com",
            path="/b/k",
            headers=lambda headers: (
                headers.get("content-type") == "application/octet-stream"
                and headers.get("x-amz-content-sha256")
                == "STREAMING-UNSIGNED-PAYLOAD-TRAILER"
                and "content-length" not in headers
            ),
            query={"x-id": "PutObject"},
        )

        client.put_object(
            PutObjectInput(
                bucket="b",
                key="k",
                body=_UnsizedStream(b"hello"),
                checksum_algorithm="SHA256",
            )
        )


@pytest.mark.parametrize(
    ("algorithm", "feature_id"),
    [
        ("SHA256", "Y"),
        ("SHA1", "X"),
        ("CRC32", "U"),
        ("CRC32C", "V"),
        ("CRC64NVME", "W"),
    ],
)
def test_should_feature_detect_checksum(algorithm: str, feature_id: str) -> None:
    """The user agent lists the feature ID for the requested checksum algorithm."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            headers={"user-agent": f"/(.*?) m/(.*?){feature_id}(.*?)$/"}
        )

        client.put_object(
            PutObjectInput(
                bucket="b", key="k", body=b"abcd", checksum_algorithm=algorithm
            )
        )


def test_should_raise_an_error_if_the_requested_algorithm_implementation_is_not_available() -> (
    None
):
    """Requesting a checksum algorithm without an implementation raises an error."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(headers={"x-amz-checksum-helloworld": HELLO_WORLD_2})

    with pytest.raises(UnsupportedChecksumAlgorithmError, match="HELLOWORLD"):
        client.put_object(
            PutObjectInput(
                bucket="bucket", key="key", body=b"hi", checksum_algorithm="HELLOWORLD"
            )
        )


def test_should_ignore_the_checksum_header_and_perform_no_checksum_validation_if_no_matching_algorithm_implementation_is_available() -> (
    None
):
    """A response checksum for an unsupported algorithm skips validation."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    mock(client).expect_request(
        hostname="bucket.s3.us-west-2.amazonaws.com"
    ).respond_with(
        headers={"x-amz-checksum-helloworld": HELLO_WORLD_2}, body=b"hi_extra_bytes"
    )

    output = client.get_object(GetObjectInput(bucket="bucket", key="key"))

    assert not isinstance(output.body, ChecksumStream)
    assert read_streaming_blob(output.body) == b"hi_extra_bytes"


class _UnsizedStream:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data)
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk
