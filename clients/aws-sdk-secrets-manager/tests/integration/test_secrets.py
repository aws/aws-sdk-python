# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Secret versioning, binary values and deletion."""

import pytest
from aws_sdk_secrets_manager.aio.client import AsyncSecretsManagerClient
from aws_sdk_secrets_manager.models import (
    CreateSecretInput,
    DeleteSecretInput,
    GetSecretValueInput,
    ListSecretVersionIdsInput,
    PutSecretValueInput,
    ResourceNotFoundException,
)

from waiters import wait_until, wait_until_gone

from . import unique_name
from .conftest import SECRET_VALUE


@pytest.mark.skip(
    reason="TODO: ClientRequestToken is not auto-filled by smithy-core 0.10; needs the idempotency-token fill from smithy-python #913"
)
async def test_new_version_rotates_current_and_previous_stages(
    secrets: AsyncSecretsManagerClient, secret_name: str
) -> None:
    """Putting a second value moves AWSCURRENT to it and AWSPREVIOUS to the first, and both stay readable."""
    original = await secrets.get_secret_value(
        GetSecretValueInput(secret_id=secret_name)
    )
    put = await secrets.put_secret_value(
        PutSecretValueInput(secret_id=secret_name, secret_string="second-value")
    )
    assert put.version_id != original.version_id

    current = await wait_until(
        lambda: secrets.get_secret_value(GetSecretValueInput(secret_id=secret_name)),
        done=lambda r: r.version_id == put.version_id,
        interval=2,
    )
    assert current.secret_string == "second-value"
    assert current.version_id == put.version_id

    previous = await wait_until(
        lambda: secrets.get_secret_value(
            GetSecretValueInput(secret_id=secret_name, version_stage="AWSPREVIOUS")
        ),
        done=lambda r: r.version_id == original.version_id,
        interval=2,
    )
    assert previous.secret_string == SECRET_VALUE
    assert previous.version_id == original.version_id

    by_id = await secrets.get_secret_value(
        GetSecretValueInput(secret_id=secret_name, version_id=original.version_id)
    )
    assert by_id.secret_string == SECRET_VALUE


@pytest.mark.skip(
    reason="TODO: ClientRequestToken is not auto-filled by smithy-core 0.10; needs the idempotency-token fill from smithy-python #913"
)
async def test_list_versions_reports_stage_labels(
    secrets: AsyncSecretsManagerClient, secret_name: str
) -> None:
    """ListSecretVersionIds returns both versions with their staging labels."""
    put = await secrets.put_secret_value(
        PutSecretValueInput(secret_id=secret_name, secret_string="second-value")
    )

    listed = await wait_until(
        lambda: secrets.list_secret_version_ids(
            ListSecretVersionIdsInput(secret_id=secret_name)
        ),
        done=lambda r: (
            len(r.versions or []) == 2
            and any(v.version_stages == ["AWSPREVIOUS"] for v in r.versions or [])
        ),
        interval=2,
    )

    stages = {v.version_id: v.version_stages for v in listed.versions or []}
    assert len(stages) == 2
    assert stages[put.version_id] == ["AWSCURRENT"]
    assert ["AWSPREVIOUS"] in stages.values()


@pytest.mark.skip(
    reason="TODO: ClientRequestToken is not auto-filled by smithy-core 0.10; needs the idempotency-token fill from smithy-python #913"
)
async def test_binary_secret_round_trip(secrets: AsyncSecretsManagerClient) -> None:
    """Bytes that are not valid UTF-8 survive a create and get round trip as a binary secret."""
    name = unique_name()
    payload = bytes(range(256))
    await secrets.create_secret(CreateSecretInput(name=name, secret_binary=payload))
    try:
        result = await wait_until(
            lambda: secrets.get_secret_value(GetSecretValueInput(secret_id=name)),
            retry_on=(ResourceNotFoundException,),
            interval=2,
        )
        assert result.secret_binary == payload
        assert result.secret_string is None
    finally:
        await secrets.delete_secret(
            DeleteSecretInput(secret_id=name, force_delete_without_recovery=True)
        )


@pytest.mark.skip(
    reason="TODO: ClientRequestToken is not auto-filled by smithy-core 0.10; needs the idempotency-token fill from smithy-python #913"
)
async def test_force_deleted_secret_is_not_found(
    secrets: AsyncSecretsManagerClient,
) -> None:
    """A secret deleted without recovery can no longer be read."""
    name = unique_name()
    await secrets.create_secret(CreateSecretInput(name=name, secret_string="x"))
    await wait_until(
        lambda: secrets.get_secret_value(GetSecretValueInput(secret_id=name)),
        retry_on=(ResourceNotFoundException,),
        interval=2,
    )
    await secrets.delete_secret(
        DeleteSecretInput(secret_id=name, force_delete_without_recovery=True)
    )

    await wait_until_gone(
        lambda: secrets.get_secret_value(GetSecretValueInput(secret_id=name)),
        gone_on=(ResourceNotFoundException,),
        interval=2,
    )
