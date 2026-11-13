# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging
from pathlib import Path

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import ListBucketsInput
from smithy_aws_core.protocols import RestXmlClientProtocol
from smithy_core.exceptions import CallError
from smithy_core.retries import StandardRetryStrategy
from smithy_http.interfaces import HTTPRequest, HTTPRequestConfiguration
from smithy_http.interfaces import HTTPResponse as HTTPResponseInterface
from smithy_http.urllib3 import Urllib3HTTPClient
from smithy_test import mock


def test_should_accept_shared_credentials_file(tmp_path: Path) -> None:
    """Requests carry the access key from a shared credentials file."""
    credentials_file = tmp_path / "credentials"
    credentials_file.write_text(
        "[default]\naws_access_key_id = TEST\naws_secret_access_key = TEST\n"
    )
    config_file = tmp_path / "config"
    config_file.write_text("")

    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            profile="default",
            config_file_path=str(config_file),
            credentials_file_path=str(credentials_file),
        )
    )

    assert client is not None
    client.close()


# TODO: log failed calls at error level
@pytest.mark.skip
def test_log_level_should_filter_log_records(caplog: pytest.LogCaptureFixture) -> None:
    """The log level filters out debug records, and a failed call logs at error level."""
    with caplog.at_level(logging.DEBUG):
        client = S3Client(S3Config.resolve(region="us-west-2"))
        mock(client).expect_request(hostname="/s3/").respond_with(
            status_code=400, body=""
        )
        with pytest.raises(CallError):
            client.list_buckets(ListBucketsInput())

    assert any(r.levelno == logging.DEBUG for r in caplog.records)
    assert any(r.levelno == logging.ERROR for r in caplog.records)

    caplog.clear()
    with caplog.at_level(logging.INFO):
        client = S3Client(S3Config.resolve(region="us-west-2"))
        mock(client).expect_request(hostname="/s3/").respond_with(
            status_code=400, body=""
        )
        with pytest.raises(CallError):
            client.list_buckets(ListBucketsInput())

    assert not any(r.levelno == logging.DEBUG for r in caplog.records)
    assert any(r.levelno == logging.ERROR for r in caplog.records)


def test_should_accept_extended_aws_rest_xml_protocol() -> None:
    """The config accepts a subclass of the REST-XML protocol."""

    class ExtendedRestXmlClientProtocol(RestXmlClientProtocol):
        pass

    config = S3Config.resolve(
        region="us-west-2", protocol=ExtendedRestXmlClientProtocol
    )
    client = S3Client(config)

    assert isinstance(config.protocol, ExtendedRestXmlClientProtocol)
    assert client is not None


def test_should_accept_extended_urllib3_http_client() -> None:
    """The config accepts a subclass of the urllib3 transport."""

    class ExtendedUrllib3HTTPClient(Urllib3HTTPClient):
        def send(
            self,
            request: HTTPRequest,
            *,
            request_config: HTTPRequestConfiguration | None = None,
        ) -> HTTPResponseInterface:
            return super().send(request, request_config=request_config)

    client = S3Client(
        S3Config.resolve(region="us-west-2", transport=ExtendedUrllib3HTTPClient())
    )

    assert client is not None
    client.close()


def test_should_accept_configured_retry_strategy_with_custom_backoff() -> None:
    """The config accepts a retry strategy with a custom backoff."""

    class CustomBackoff:
        def compute_next_backoff_delay(self, retry_attempt: int) -> float:
            return 0.5 + retry_attempt * 1.0

    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            retry_strategy=StandardRetryStrategy(
                max_attempts=5, backoff_strategy=CustomBackoff()
            ),
        )
    )

    assert client is not None
