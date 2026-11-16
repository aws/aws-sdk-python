# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import logging

from aws_sdk_cloudfront.client import CloudFrontClient
from aws_sdk_cloudfront.config import CloudFrontConfig
from aws_sdk_cloudfront.models import ListDistributionsInput
from pytest import LogCaptureFixture
from smithy_test import mock


def test_debug_logging_should_have_no_effect_on_request_creation(
    caplog: LogCaptureFixture,
) -> None:
    """Debug logging leaves the serialized request unchanged."""
    caplog.set_level(logging.DEBUG)
    client = CloudFrontClient(CloudFrontConfig.resolve(region="us-west-2"))
    mock(client).expect_request(
        method="GET",
        hostname="cloudfront.amazonaws.com",
        scheme="https",
        path="/2020-05-31/distribution",
    )

    client.list_distributions(ListDistributionsInput())
