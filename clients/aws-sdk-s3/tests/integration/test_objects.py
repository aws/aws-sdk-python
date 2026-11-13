# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Object operations, from JS v3 s3-object-features.e2e and S3.e2e."""

import base64
import hashlib
import io
import os
from pathlib import Path

import pytest
from aws_sdk_s3.aio.client import AsyncS3Client
from aws_sdk_s3.models import (
    CopyObjectInput,
    Delete,
    DeleteObjectInput,
    DeleteObjectsInput,
    GetObjectInput,
    HeadObjectInput,
    ListObjectsV2Input,
    ObjectIdentifier,
    PutObjectInput,
)

from . import read_body


def _key(name: str) -> str:
    return f"objects/{os.urandom(4).hex()}/{name}"


async def test_object_crud(s3: AsyncS3Client, bucket: str) -> None:
    key = _key("crud.txt")
    put = await s3.put_object(
        PutObjectInput(bucket=bucket, key=key, body=b"hello", content_type="text/plain")
    )
    assert put.e_tag is not None

    head = await s3.head_object(HeadObjectInput(bucket=bucket, key=key))
    assert head.content_length == 5
    assert head.content_type == "text/plain"
    assert head.e_tag == put.e_tag

    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == b"hello"

    await s3.delete_object(DeleteObjectInput(bucket=bucket, key=key))
    listed = await s3.list_objects_v2(ListObjectsV2Input(bucket=bucket, prefix=key))
    assert not listed.contents


@pytest.mark.parametrize(
    "name",
    [
        "with space",
        "plus+sign",
        "percent%41encoded",
        "question?mark#hash",
        "tilde~and!*'()",
        "unicode-日本語-ü",
        "colon:semi;comma,equals=",
        "trailing.",
        "../leading/dot/segment",
        "embedded/./dot/../segments",
    ],
)
async def test_keys_with_special_characters(
    s3: AsyncS3Client, bucket: str, name: str
) -> None:
    key = _key(name)
    await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=name.encode()))

    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == name.encode()

    listed = await s3.list_objects_v2(ListObjectsV2Input(bucket=bucket, prefix=key))
    assert [obj.key for obj in listed.contents or []] == [key]

    await s3.delete_object(DeleteObjectInput(bucket=bucket, key=key))


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"", id="empty"),
        pytest.param("héllo wörld 你好 🌍".encode(), id="multibyte"),
        pytest.param(os.urandom(1024), id="1KiB"),
        pytest.param(os.urandom(8 * 1024 * 1024), id="8MiB"),
    ],
)
async def test_bytes_bodies(s3: AsyncS3Client, bucket: str, body: bytes) -> None:
    key = _key("bytes")
    await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=body))

    head = await s3.head_object(HeadObjectInput(bucket=bucket, key=key))
    assert head.content_length == len(body)
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == body


async def test_stream_body(s3: AsyncS3Client, bucket: str) -> None:
    body = os.urandom(256 * 1024)
    key = _key("stream")
    await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=io.BytesIO(body)))
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == body


@pytest.mark.parametrize(
    "size", [0, 1024, 6 * 1024 * 1024], ids=["empty", "small", "large"]
)
async def test_file_body(
    s3: AsyncS3Client, bucket: str, tmp_path: Path, size: int
) -> None:
    data = os.urandom(size)
    path = tmp_path / "upload.bin"
    path.write_bytes(data)
    key = _key("file")
    with path.open("rb") as f:
        await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=f))
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=key))
    assert await read_body(output.body) == data


async def test_ranged_get(s3: AsyncS3Client, bucket: str) -> None:
    key = _key("range")
    await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=b"0123456789"))
    output = await s3.get_object(
        GetObjectInput(bucket=bucket, key=key, range="bytes=2-5")
    )
    assert await read_body(output.body) == b"2345"
    assert output.content_range == "bytes 2-5/10"


async def test_user_metadata(s3: AsyncS3Client, bucket: str) -> None:
    key = _key("metadata")
    await s3.put_object(
        PutObjectInput(
            bucket=bucket, key=key, body=b"x", metadata={"owner": "sdk", "run": "integ"}
        )
    )
    head = await s3.head_object(HeadObjectInput(bucket=bucket, key=key))
    assert head.metadata == {"owner": "sdk", "run": "integ"}


@pytest.mark.parametrize(
    "expires",
    [
        pytest.param("Wed, 02 Jan 2030 03:04:05 GMT", id="http-date"),
        # The header is free text, so a value that isn't a date still round-trips.
        pytest.param("not a date", id="invalid"),
    ],
)
async def test_expires_round_trips_as_string(
    s3: AsyncS3Client, bucket: str, expires: str
) -> None:
    key = _key("expires")
    await s3.put_object(
        PutObjectInput(bucket=bucket, key=key, body=b"x", expires=expires)
    )
    head = await s3.head_object(HeadObjectInput(bucket=bucket, key=key))
    assert head.expires == expires


async def test_copy_object(s3: AsyncS3Client, bucket: str) -> None:
    source = _key("copy-source")
    target = _key("copy-target")
    await s3.put_object(PutObjectInput(bucket=bucket, key=source, body=b"copied"))
    await s3.copy_object(
        CopyObjectInput(bucket=bucket, key=target, copy_source=f"{bucket}/{source}")
    )
    output = await s3.get_object(GetObjectInput(bucket=bucket, key=target))
    assert await read_body(output.body) == b"copied"


async def test_delete_objects(s3: AsyncS3Client, bucket: str) -> None:
    keys = [_key(f"batch-{i}") for i in range(3)]
    for key in keys:
        await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=b"x"))

    # DeleteObjects requires a request checksum, which the client adds.
    result = await s3.delete_objects(
        DeleteObjectsInput(
            bucket=bucket,
            delete=Delete(objects=[ObjectIdentifier(key=key) for key in keys]),
        )
    )
    assert sorted(d.key for d in result.deleted or [] if d.key) == sorted(keys)
    assert not result.errors


async def test_list_objects_v2_pages(s3: AsyncS3Client, bucket: str) -> None:
    prefix = _key("pages/")
    keys = [f"{prefix}{i}" for i in range(5)]
    for key in keys:
        await s3.put_object(PutObjectInput(bucket=bucket, key=key, body=b"x"))

    seen: list[str] = []
    token: str | None = None
    while True:
        page = await s3.list_objects_v2(
            ListObjectsV2Input(
                bucket=bucket, prefix=prefix, max_keys=2, continuation_token=token
            )
        )
        seen.extend(obj.key for obj in page.contents or [] if obj.key)
        if not page.is_truncated:
            break
        token = page.next_continuation_token
    assert seen == keys


@pytest.mark.skip(reason="Paginators are not implemented.")
async def test_list_objects_v2_paginator() -> None: ...


@pytest.mark.skip(reason="Waiters are not implemented.")
async def test_object_exists_waiter() -> None: ...


async def test_sse_c_with_caller_computed_key_md5(
    s3: AsyncS3Client, bucket: str
) -> None:
    key = _key("sse-c")
    secret = os.urandom(32)
    customer_key = base64.b64encode(secret).decode()
    key_md5 = base64.b64encode(
        hashlib.md5(secret, usedforsecurity=False).digest()
    ).decode()
    await s3.put_object(
        PutObjectInput(
            bucket=bucket,
            key=key,
            body=b"secret",
            sse_customer_algorithm="AES256",
            sse_customer_key=customer_key,
            sse_customer_key_md5=key_md5,
        )
    )
    output = await s3.get_object(
        GetObjectInput(
            bucket=bucket,
            key=key,
            sse_customer_algorithm="AES256",
            sse_customer_key=customer_key,
            sse_customer_key_md5=key_md5,
        )
    )
    assert await read_body(output.body) == b"secret"
    assert output.sse_customer_algorithm == "AES256"


@pytest.mark.skip(
    reason="Deriving the SSE-C key MD5 and encoding from the raw key is not implemented."
)
async def test_sse_c_key_md5_derived_from_key() -> None: ...


@pytest.mark.skip(
    reason="Sending Expect: 100-continue for large bodies is not implemented."
)
async def test_expect_continue_for_large_bodies() -> None: ...


@pytest.mark.skip(reason="Presigned URLs are not implemented.")
async def test_presigned_get_and_put() -> None: ...


@pytest.mark.skip(reason="Presigned POST policies are not implemented.")
async def test_presigned_post() -> None: ...
