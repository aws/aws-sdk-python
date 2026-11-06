# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from typing import Unpack

import pytest
from smithy_core import URI
from smithy_core.aio.types import AsyncBytesReader
from smithy_core.types import TypedProperties
from smithy_http.testing import MockHTTPClient

from aws_sdk_bedrock_runtime.config import (
    AsyncBedrockRuntimeConfig,
    _AsyncBedrockRuntimeConfigOverrides,
)
from aws_sdk_bedrock_runtime.models import (
    CONVERSE,
    CONVERSE_STREAM,
    INVOKE_MODEL,
    INVOKE_MODEL_WITH_RESPONSE_STREAM,
    ContentBlockText,
    ConverseInput,
    ConverseStreamInput,
    InvokeModelInput,
    InvokeModelWithResponseStreamInput,
    Message,
)


@pytest.fixture(autouse=True)
def isolate_aws_compression_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in (
        "AWS_DISABLE_REQUEST_COMPRESSION",
        "AWS_REQUEST_MIN_COMPRESSION_SIZE_BYTES",
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
    ):
        monkeypatch.delenv(variable, raising=False)


async def resolve_config(
    tmp_path: Path, **overrides: Unpack[_AsyncBedrockRuntimeConfigOverrides]
) -> AsyncBedrockRuntimeConfig:
    resolved_overrides: _AsyncBedrockRuntimeConfigOverrides = {
        "region": "us-west-2",
        "transport": MockHTTPClient(),
        **overrides,
    }
    return await AsyncBedrockRuntimeConfig.resolve(
        config_file_path=str(tmp_path / "config"),
        credentials_file_path=str(tmp_path / "credentials"),
        **resolved_overrides,
    )


async def test_compression_defaults_are_available_on_generated_config(
    tmp_path: Path,
) -> None:
    config = await resolve_config(tmp_path)
    assert config.disable_request_compression is False
    assert config.request_min_compression_size_bytes == 10240


@pytest.mark.parametrize("minimum_size", [0, 10485760])
async def test_compression_threshold_boundaries_survive_generated_config_resolution(
    tmp_path: Path, minimum_size: int
) -> None:
    config = await resolve_config(
        tmp_path, request_min_compression_size_bytes=minimum_size
    )
    assert config.request_min_compression_size_bytes == minimum_size


async def test_standard_compression_settings_resolve_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_DISABLE_REQUEST_COMPRESSION", "true")
    monkeypatch.setenv("AWS_REQUEST_MIN_COMPRESSION_SIZE_BYTES", "256")
    config = await resolve_config(tmp_path)
    assert config.disable_request_compression is True
    assert config.request_min_compression_size_bytes == 256


async def test_client_settings_override_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_DISABLE_REQUEST_COMPRESSION", "true")
    monkeypatch.setenv("AWS_REQUEST_MIN_COMPRESSION_SIZE_BYTES", "256")
    config = await resolve_config(
        tmp_path,
        disable_request_compression=False,
        request_min_compression_size_bytes=0,
    )
    assert config.disable_request_compression is False
    assert config.request_min_compression_size_bytes == 0


@pytest.mark.parametrize(
    "kind", ["converse", "converse-stream", "invoke", "invoke-with-response-stream"]
)
@pytest.mark.parametrize("minimum_size", [None, 0])
async def test_unsupported_bedrock_request_stays_uncompressed(
    tmp_path: Path, kind: str, minimum_size: int | None
) -> None:
    if minimum_size is None:
        config = await resolve_config(tmp_path)
    else:
        config = await resolve_config(
            tmp_path, request_min_compression_size_bytes=minimum_size
        )
    assert config.protocol is not None
    messages = [Message(role="user", content=[ContentBlockText(value="hello")])]
    if kind == "converse":
        operation, input = (
            CONVERSE,
            ConverseInput(model_id="test-model", messages=messages),
        )
    elif kind == "converse-stream":
        operation, input = (
            CONVERSE_STREAM,
            ConverseStreamInput(model_id="test-model", messages=messages),
        )
    elif kind == "invoke":
        operation, input = (
            INVOKE_MODEL,
            InvokeModelInput(
                model_id="test-model",
                body=b'{"prompt":"hello"}',
                content_type="application/json",
            ),
        )
    else:
        operation, input = (
            INVOKE_MODEL_WITH_RESPONSE_STREAM,
            InvokeModelWithResponseStreamInput(
                model_id="test-model",
                body=b'{"prompt":"hello"}',
                content_type="application/json",
            ),
        )
    request = config.protocol.serialize_request(
        operation=operation,
        input=input,
        endpoint=URI(host="bedrock-runtime.us-west-2.amazonaws.com"),
        context=TypedProperties({"config": config}),
    )
    assert "Content-Encoding" not in request.fields
    assert request.method == "POST"
    assert request.destination.path == f"/model/test-model/{kind}"
    assert request.fields["Content-Type"].as_string() == "application/json"
    wire = await AsyncBytesReader(request.body).read()
    if kind.startswith("converse"):
        assert wire == b'{"messages":[{"role":"user","content":[{"text":"hello"}]}]}'
    else:
        assert wire == b'{"prompt":"hello"}'
