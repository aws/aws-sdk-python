# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import re

from aws_sdk_ec2.client import EC2Client
from aws_sdk_ec2.config import EC2Config
from aws_sdk_ec2.models import (
    InstanceIpv6Address,
    InstanceNetworkInterfaceSpecification,
    PrivateIpAddressSpecification,
    RequestSpotFleetInput,
    RequestSpotInstancesInput,
    RequestSpotLaunchSpecification,
    RunInstancesInput,
    SpotFleetLaunchSpecification,
    SpotFleetRequestConfigData,
)
from smithy_test import mock


def test_should_serialize_based_on_ec2_query_name_if_present_run_instances() -> None:
    """RunInstances members serialize under their ec2QueryName trait value."""
    client = EC2Client(EC2Config.resolve(region="us-east-1"))

    def has_params(body: bytes) -> None:
        params = sorted(body.decode().split("&"))
        assert params[0] == "Action=RunInstances"
        assert re.fullmatch(r"ClientToken=(.*?)", params[1])
        assert params[2:] == [
            "DryRun=true",
            "MaxCount=1",
            "MinCount=0",
            "NetworkInterface.1.Ipv6Addresses.1.Ipv6Address=xx",
            "NetworkInterface.1.PrivateIpAddresses.1.PrivateIpAddress=xx",
            "Version=2016-11-15",
        ]

    mock(client).expect_request(body=has_params)

    client.run_instances(
        RunInstancesInput(
            dry_run=True,
            max_count=1,
            min_count=0,
            network_interfaces=[
                InstanceNetworkInterfaceSpecification(
                    private_ip_addresses=[
                        PrivateIpAddressSpecification(private_ip_address="xx")
                    ],
                    ipv6_addresses=[InstanceIpv6Address(ipv6_address="xx")],
                )
            ],
        )
    )


def test_should_serialize_based_on_ec2_query_name_if_present_request_spot_instances() -> (
    None
):
    """RequestSpotInstances members serialize under their ec2QueryName trait value."""
    client = EC2Client(EC2Config.resolve(region="us-east-1"))

    def has_params(body: bytes) -> None:
        assert sorted(body.decode().split("&")) == [
            "Action=RequestSpotInstances",
            "DryRun=true",
            "LaunchSpecification.NetworkInterface.1.Ipv6Addresses.1.Ipv6Address=xx",
            "LaunchSpecification.NetworkInterface.1.PrivateIpAddresses.1.PrivateIpAddress=xx",
            "Version=2016-11-15",
        ]

    mock(client).expect_request(body=has_params)

    client.request_spot_instances(
        RequestSpotInstancesInput(
            dry_run=True,
            launch_specification=RequestSpotLaunchSpecification(
                network_interfaces=[
                    InstanceNetworkInterfaceSpecification(
                        private_ip_addresses=[
                            PrivateIpAddressSpecification(private_ip_address="xx")
                        ],
                        ipv6_addresses=[InstanceIpv6Address(ipv6_address="xx")],
                    )
                ]
            ),
        )
    )


def test_should_serialize_based_on_ec2_query_name_if_present_request_spot_fleet() -> (
    None
):
    """RequestSpotFleet members serialize under their ec2QueryName trait value."""
    client = EC2Client(EC2Config.resolve(region="us-east-1"))

    def has_params(body: bytes) -> None:
        assert sorted(body.decode().split("&")) == [
            "Action=RequestSpotFleet",
            "DryRun=true",
            "SpotFleetRequestConfig.IamFleetRole=",
            "SpotFleetRequestConfig.LaunchSpecifications.1.NetworkInterfaceSet.1.Ipv6Addresses.1.Ipv6Address=xx",
            "SpotFleetRequestConfig.LaunchSpecifications.1.NetworkInterfaceSet.1.PrivateIpAddresses.1.PrivateIpAddress=xx",
            "SpotFleetRequestConfig.TargetCapacity=0",
            "Version=2016-11-15",
        ]

    mock(client).expect_request(body=has_params)

    client.request_spot_fleet(
        RequestSpotFleetInput(
            dry_run=True,
            spot_fleet_request_config=SpotFleetRequestConfigData(
                iam_fleet_role="",
                target_capacity=0,
                launch_specifications=[
                    SpotFleetLaunchSpecification(
                        network_interfaces=[
                            InstanceNetworkInterfaceSpecification(
                                private_ip_addresses=[
                                    PrivateIpAddressSpecification(
                                        private_ip_address="xx"
                                    )
                                ],
                                ipv6_addresses=[InstanceIpv6Address(ipv6_address="xx")],
                            )
                        ]
                    )
                ],
            ),
        )
    )
