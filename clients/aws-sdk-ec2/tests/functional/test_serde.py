# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from urllib.parse import parse_qsl

from aws_sdk_ec2.client import EC2Client
from aws_sdk_ec2.config import EC2Config
from aws_sdk_ec2.models import ConnectionLogOptions, CreateClientVpnEndpointInput
from smithy_test import mock


def test_should_serialize_query() -> None:
    """CreateClientVpnEndpoint serializes as a form-encoded EC2 query body posted to the root path."""
    client = EC2Client(EC2Config.resolve(region="us-west-2"))

    def has_params(body: bytes) -> None:
        params = dict(parse_qsl(body.decode(), keep_blank_values=True))
        assert (
            params.items()
            >= {
                "Action": "CreateClientVpnEndpoint",
                "Version": "2016-11-15",
                "ClientCidrBlock": "ClientCidrBlock",
                "ServerCertificateArn": "ServerCertificateArn",
            }.items()
        )

    mock(client).expect_request(
        method="POST",
        hostname="ec2.us-west-2.amazonaws.com",
        headers={"content-type": "application/x-www-form-urlencoded"},
        body=has_params,
        scheme="https",
        path="/",
    )

    client.create_client_vpn_endpoint(
        CreateClientVpnEndpointInput(
            client_cidr_block="ClientCidrBlock",
            server_certificate_arn="ServerCertificateArn",
            authentication_options=[],
            connection_log_options=ConnectionLogOptions(),
        )
    )
