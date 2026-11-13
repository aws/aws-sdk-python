# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Flexible checksums, from JS v3 middleware-flexible-checksums and checksum-s3."""

import os

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.models import (
    ChecksumAlgorithm,
    ChecksumMode,
    GetObjectInput,
    HeadObjectInput,
    PutObjectInput,
)

from . import read_body

# Algorithms the client computes itself; MD5 must be supplied by the caller.
_ALGORITHMS = [
    ChecksumAlgorithm.CRC32,
    ChecksumAlgorithm.CRC32_C,
    ChecksumAlgorithm.CRC64_NVME,
    ChecksumAlgorithm.SHA1,
    ChecksumAlgorithm.SHA256,
    ChecksumAlgorithm.SHA512,
    ChecksumAlgorithm.XXHASH64,
    ChecksumAlgorithm.XXHASH3,
    ChecksumAlgorithm.XXHASH128,
]

# Lengths around the chunk and block sizes the implementations use.
_SIZES = [0, 1, 63, 64, 65, 1023, 1024, 1025, 64 * 1024 + 1]


def _checksum_field(algorithm: ChecksumAlgorithm) -> str:
    return "checksum_" + {
        ChecksumAlgorithm.CRC32_C: "crc32_c",
        ChecksumAlgorithm.CRC64_NVME: "crc64_nvme",
    }.get(algorithm, algorithm.value.lower())


@pytest.mark.parametrize("algorithm", _ALGORITHMS, ids=lambda a: a.value)
async def test_put_and_validate(
    s3: AsyncS3Client, bucket: str, algorithm: ChecksumAlgorithm
) -> None:
    key = f"checksums/{algorithm.value}/{os.urandom(4).hex()}"
    body = os.urandom(4096)
    put = await s3.put_object(
        PutObjectInput(bucket=bucket, key=key, body=body, checksum_algorithm=algorithm)
    )
    field = _checksum_field(algorithm)
    sent = getattr(put, field)
    assert sent

    output = await s3.get_object(
        GetObjectInput(bucket=bucket, key=key, checksum_mode=ChecksumMode.ENABLED)
    )
    assert await read_body(output.body) == body
    assert getattr(output, field) == sent


@pytest.mark.parametrize("size", _SIZES)
@pytest.mark.parametrize("algorithm", _ALGORITHMS, ids=lambda a: a.value)
async def test_round_trip_across_byte_lengths(
    s3: AsyncS3Client, bucket: str, algorithm: ChecksumAlgorithm, size: int
) -> None:
    key = f"checksums/sizes/{algorithm.value}/{size}"
    body = os.urandom(size)
    await s3.put_object(
        PutObjectInput(bucket=bucket, key=key, body=body, checksum_algorithm=algorithm)
    )
    output = await s3.get_object(
        GetObjectInput(bucket=bucket, key=key, checksum_mode=ChecksumMode.ENABLED)
    )
    assert await read_body(output.body) == body


async def test_default_request_checksum_is_crc64_nvme(
    s3: AsyncS3Client, bucket: str
) -> None:
    key = f"checksums/default/{os.urandom(4).hex()}"
    put = await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=b"default"))
    assert put.checksum_crc64_nvme

    head = await s3.head_object(
        HeadObjectInput(bucket=bucket, key=key, checksum_mode=ChecksumMode.ENABLED)
    )
    assert head.checksum_crc64_nvme == put.checksum_crc64_nvme


@pytest.mark.skip(
    reason="Request checksums for bodies of unknown length are not implemented."
)
async def test_unknown_length_stream_with_trailing_checksum() -> None: ...
