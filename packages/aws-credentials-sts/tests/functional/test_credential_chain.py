#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import sys
from pathlib import Path

import pytest
from aws_sdk_s3.client import S3Client
from aws_sdk_s3.config import S3Config
from aws_sdk_s3.models import ListBucketsInput
from smithy_aws_core.identity.chain import IdentityChainError

from ._transports import CredentialSourceTransport, fake_imds, signing_access_key

# CAUTION: these tests pin the order credential sources are tried in. Customers rely
# on it staying the same across upgrades, whatever the specification says.


def test_each_source_is_used_until_it_is_gone(
    isolated_environment: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Removing each credential source in chain order hands over to the next."""
    process = tmp_path / "credential_process.py"
    process.write_text(
        "import json\n"
        "print(json.dumps({'Version': 1, 'AccessKeyId': 'PROCESS_AKID',"
        " 'SecretAccessKey': 'SECRET'}))\n"
    )
    token_file = tmp_path / "web_identity_token"
    token_file.write_text("web-identity-token")
    env = isolated_environment

    env.setenv("AWS_ACCESS_KEY_ID", "ENV_AKID")
    env.setenv("AWS_SECRET_ACCESS_KEY", "SECRET")
    env.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/env-web-role")
    env.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", str(token_file))
    env.setenv("AWS_CONTAINER_CREDENTIALS_FULL_URI", "http://127.0.0.1/credentials")
    (tmp_path / "config").write_text(
        "[default]\n"
        "region = us-west-2\n"
        "role_arn = arn:aws:iam::123456789012:role/profile-role\n"
        "source_profile = base\n"
        f"web_identity_token_file = {token_file}\n"
        f"credential_process = {sys.executable} {process}\n"
        "[profile base]\n"
        "region = us-west-2\n"
    )
    (tmp_path / "credentials").write_text(
        "[default]\n"
        "aws_access_key_id = SESSION_AKID\n"
        "aws_secret_access_key = SECRET\n"
        "aws_session_token = TOKEN\n"
        "[base]\n"
        "aws_access_key_id = BASE_AKID\n"
        "aws_secret_access_key = SECRET\n"
    )

    # Environment variables
    assert _signing_access_key() == "ENV_AKID"

    # Web identity from environment variables
    env.delenv("AWS_ACCESS_KEY_ID")
    env.delenv("AWS_SECRET_ACCESS_KEY")
    assert _signing_access_key() == "AssumeRoleWithWebIdentity.env-web-role"

    # Profile role assumption with a source profile
    env.delenv("AWS_ROLE_ARN")
    env.delenv("AWS_WEB_IDENTITY_TOKEN_FILE")
    assert _signing_access_key() == "AssumeRole.profile-role"

    # Profile web identity
    (tmp_path / "config").write_text(
        "[default]\n"
        "region = us-west-2\n"
        "role_arn = arn:aws:iam::123456789012:role/profile-role\n"
        f"web_identity_token_file = {token_file}\n"
        f"credential_process = {sys.executable} {process}\n"
    )
    assert _signing_access_key() == "AssumeRoleWithWebIdentity.profile-role"

    # Profile session keys. A profile with role_arn never uses its own keys, so
    # they only take effect once the role is gone.
    (tmp_path / "config").write_text(
        f"[default]\nregion = us-west-2\ncredential_process = {sys.executable} {process}\n"
    )
    assert _signing_access_key() == "SESSION_AKID"

    # Profile static keys
    (tmp_path / "credentials").write_text(
        "[default]\naws_access_key_id = STATIC_AKID\naws_secret_access_key = SECRET\n"
    )
    assert _signing_access_key() == "STATIC_AKID"

    # Profile credential process
    (tmp_path / "credentials").write_text("")
    assert _signing_access_key() == "PROCESS_AKID"

    # Container credentials
    (tmp_path / "config").write_text("[default]\nregion = us-west-2\n")
    assert _signing_access_key() == "ECS_AKID"

    # EC2 instance metadata
    env.delenv("AWS_CONTAINER_CREDENTIALS_FULL_URI")
    with fake_imds() as endpoint:
        env.setenv("AWS_EC2_METADATA_SERVICE_ENDPOINT", endpoint)
        assert _signing_access_key() == "IMDS_AKID"

    # No source left
    env.setenv("AWS_EC2_METADATA_DISABLED", "true")
    with pytest.raises(IdentityChainError):
        _signing_access_key()


def _signing_access_key() -> str:
    transport = CredentialSourceTransport()
    client = S3Client(S3Config.resolve(region="us-west-2", transport=transport))
    client.list_buckets(ListBucketsInput())
    return signing_access_key(transport)
