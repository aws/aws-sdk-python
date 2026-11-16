# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import (
    AccessControlPolicy,
    Grant,
    Grantee,
    Owner,
    PutBucketAclInput,
)
from smithy_test import mock


# TODO: decide whether XML bodies include the XML declaration and which attribute order to use
@pytest.mark.skip
def test_should_serialize_xml() -> None:
    """PutBucketAcl serializes its body as the expected XML document."""
    client = S3Client(S3Config.resolve(region="us-west-2"))
    with mock(client) as controller:
        controller.expect_request(
            method="PUT",
            hostname="s3.us-west-2.amazonaws.com",
            body='<?xml version="1.0" encoding="UTF-8"?><AccessControlPolicy xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><AccessControlList><Grant><Grantee xsi:type="CanonicalUser" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><DisplayName>STRING_VALUE</DisplayName><EmailAddress>STRING_VALUE</EmailAddress><ID>STRING_VALUE</ID><URI>STRING_VALUE</URI></Grantee><Permission>READ</Permission></Grant></AccessControlList><Owner><DisplayName>STRING_VALUE</DisplayName><ID>STRING_VALUE</ID></Owner></AccessControlPolicy>',
            scheme="https",
            path="/STRING_VALUE/",
            headers={
                "content-type": "application/xml",
                "x-amz-acl": "private",
                "content-length": "509",
                "x-amz-checksum-crc32": "XnKFaw==",
                "x-amz-content-sha256": "c0a89780e1aac5dfa17604e9e25616e7babba0b655db189be49b4c352543bb22",
            },
            query={"acl": ""},
        )

        client.put_bucket_acl(
            PutBucketAclInput(
                acl="private",
                access_control_policy=AccessControlPolicy(
                    grants=[
                        Grant(
                            grantee=Grantee(
                                display_name="STRING_VALUE",
                                email_address="STRING_VALUE",
                                id="STRING_VALUE",
                                uri="STRING_VALUE",
                                type="CanonicalUser",
                            ),
                            permission="READ",
                        )
                    ],
                    owner=Owner(display_name="STRING_VALUE", id="STRING_VALUE"),
                ),
                bucket="STRING_VALUE",
            )
        )
