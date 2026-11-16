# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_ec2.client import EC2Client
from aws_sdk_ec2.config import EC2Config
from aws_sdk_ec2.models import ConnectionLogOptions, CreateClientVpnEndpointInput
from smithy_test import mock


# TODO: decide whether non-S3 SigV4 requests send x-amz-content-sha256
@pytest.mark.skip
def test_sign_requests_in_the_header() -> None:
    """The client signs EC2 requests with SigV4 headers that include the payload hash."""
    client = EC2Client(EC2Config.resolve(region="us-west-2"))
    mock(client).expect_request(
        headers={
            "x-amz-date": r"/\d{8}T\d+Z/",
            "x-amz-content-sha256": r"/\w{30}\w+/",
            "authorization": r"/AWS4-HMAC-SHA256 Credential=(.+)\/(.+)\/(.+)\/(.+)\/aws4_request, SignedHeaders=(.+), Signature=(.+)/",
        }
    )

    client.create_client_vpn_endpoint(
        CreateClientVpnEndpointInput(
            client_cidr_block="ClientCidrBlock",
            server_certificate_arn="ServerCertificateArn",
            authentication_options=[],
            connection_log_options=ConnectionLogOptions(),
        )
    )
