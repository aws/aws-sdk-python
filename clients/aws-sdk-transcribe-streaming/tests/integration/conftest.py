# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Transcribe Streaming integration tests.

Creates and tears down an IAM role and S3 bucket needed for medical scribe
integration tests once per test session. The ``healthscribe_resources``
fixture provides the role ARN and bucket name.
"""

import json
import uuid
from typing import TYPE_CHECKING, Any

import boto3
import pytest

# The stubs are a pyright-only test dependency; the annotations using them are
# on local variables, which are never evaluated at runtime.
if TYPE_CHECKING:
    from types_boto3_iam import IAMClient
    from types_boto3_s3 import S3Client
    from types_boto3_sts import STSClient

REGION = "us-east-1"

# Tags applied to all resources so orphaned resources from interrupted
# test runs can be discovered and cleaned up.
_TAGS = [{"Key": "Purpose", "Value": "IntegTest"}]


def _create_iam_role(iam_client: Any, role_name: str, bucket_name: str) -> None:
    """Create an IAM role with S3 PutObject access for Transcribe Streaming.

    Args:
        iam_client: A boto3 IAM client.
        role_name: The name of the IAM role to create.
        bucket_name: The name of the S3 bucket the role is allowed to write to.
    """
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": ["transcribe.streaming.amazonaws.com"]},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Tags=_TAGS,
    )

    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:PutObject"],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*",
                ],
                "Effect": "Allow",
            }
        ],
    }

    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName="healthscribe-s3-access",
        PolicyDocument=json.dumps(permissions_policy),
    )


def _create_healthscribe_resources(
    iam_client: Any, s3_client: Any, sts_client: Any, role_name: str, bucket_name: str
) -> str:
    """Create an IAM role and S3 bucket for medical scribe tests.

    Args:
        iam_client: A boto3 IAM client.
        s3_client: A boto3 S3 client.
        sts_client: A boto3 STS client.
        role_name: The name of the IAM role to create.
        bucket_name: The name of the S3 bucket to create.

    Returns:
        The IAM role ARN.
    """
    account_id = sts_client.get_caller_identity()["Account"]

    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": _TAGS})
    _create_iam_role(iam_client, role_name, bucket_name)

    return f"arn:aws:iam::{account_id}:role/{role_name}"


def _delete_healthscribe_resources(
    iam_client: Any, s3_client: Any, role_name: str, bucket_name: str
) -> None:
    """Delete the IAM role and S3 bucket created for tests.

    Args:
        iam_client: A boto3 IAM client.
        s3_client: A boto3 S3 client.
        role_name: The name of the IAM role to delete.
        bucket_name: The name of the S3 bucket to delete.
    """
    # Empty and delete the bucket
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get("Contents")
            if not objects:
                continue
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={"Objects": [{"Key": o["Key"]} for o in objects]},
            )
        s3_client.delete_bucket(Bucket=bucket_name)
    except s3_client.exceptions.NoSuchBucket:
        pass

    # Delete inline policy then role
    try:
        iam_client.delete_role_policy(
            RoleName=role_name, PolicyName="healthscribe-s3-access"
        )
    except iam_client.exceptions.NoSuchEntityException:
        pass

    try:
        iam_client.delete_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException:
        pass


@pytest.fixture(scope="session")
def healthscribe_resources():
    """Create HealthScribe resources for the test session and delete them after."""
    # Shortened UUID to keep IAM role name under the 64-character limit.
    unique_suffix = uuid.uuid4().hex[:16]
    role_name = f"integ-test-transcribe-streaming-role-{unique_suffix}"
    bucket_name = f"integ-test-transcribe-streaming-bucket-{unique_suffix}"

    iam_client: IAMClient = boto3.client("iam")
    s3_client: S3Client = boto3.client("s3", region_name=REGION)
    sts_client: STSClient = boto3.client("sts")

    try:
        role_arn = _create_healthscribe_resources(
            iam_client, s3_client, sts_client, role_name, bucket_name
        )
        yield role_arn, bucket_name
    finally:
        _delete_healthscribe_resources(iam_client, s3_client, role_name, bucket_name)
