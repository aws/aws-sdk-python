# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import platform
import re

import pytest
import smithy_aws_core
from aws_sdk_s3 import __version__ as s3_version
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import ListBucketsInput
from smithy_test import mock


# TODO: decide whether the api/ user agent component uses the lowercase service ID
@pytest.mark.skip
def test_populates_user_agent_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """The user agent names the SDK, service, platform and language versions."""
    monkeypatch.delenv("AWS_SDK_UA_APP_ID", raising=False)
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            headers={
                # CAUTION: the mock always supplies static credentials, so the
                # credential feature is CREDENTIALS_CODE (e), not env vars (g).
                "user-agent": (
                    f"/^aws-sdk-python/{re.escape(smithy_aws_core.__version__)}"
                    rf"(?: \S+)* ua/2\.1 api/s3#{re.escape(s3_version)}"
                    f" os/{re.escape(platform.system().lower())}"
                    f"#{re.escape(platform.release())}"
                    rf"(?: \S+)* lang/python#{re.escape(platform.python_version())}"
                    r"(?: \S+)* m/E,e$/"
                )
            }
        )

        client.list_buckets(ListBucketsInput())


# TODO: decide whether the app ID keeps # and goes at the end of the user agent
@pytest.mark.skip
def test_should_allow_characters_from_the_set_0_9_a_za_z(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The app ID keeps the characters that the user agent format permits."""
    monkeypatch.delenv("AWS_SDK_UA_APP_ID", raising=False)
    client = S3Client(
        S3Config.resolve(
            region="us-west-2",
            sdk_ua_app_id="!#$%&'*+-.^_`|~abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )
    )
    with mock(client) as controller:
        controller.expect_request(
            headers={
                "user-agent": r"/app/!#\$%&'\*\+-\.\^_`\|~abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$/"
            }
        )

        client.list_buckets(ListBucketsInput())
