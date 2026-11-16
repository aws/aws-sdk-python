# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Encryption round trips and key aliases, from JS v3 kms-features.e2e."""

import os

import pytest
from aws_sdk_kms.aio.client import AsyncKMSClient
from aws_sdk_kms.models import (
    CreateAliasInput,
    DecryptInput,
    DeleteAliasInput,
    DescribeKeyInput,
    EncryptInput,
    InvalidCiphertextException,
    ListAliasesInput,
    NotFoundException,
)
from waiters import wait_until, wait_until_gone

from . import unique_alias_name


async def test_encrypt_decrypt_round_trips_binary_with_context(
    kms: AsyncKMSClient, key_id: str
) -> None:
    """Verifies random bytes encrypted under an encryption context decrypt back unchanged."""
    plaintext = os.urandom(512)
    context = {"purpose": "integ", "unicode": "caf\u00e9"}

    encrypted = await kms.encrypt(
        EncryptInput(key_id=key_id, plaintext=plaintext, encryption_context=context)
    )
    assert encrypted.ciphertext_blob is not None
    assert encrypted.ciphertext_blob != plaintext

    decrypted = await kms.decrypt(
        DecryptInput(
            ciphertext_blob=encrypted.ciphertext_blob, encryption_context=context
        )
    )

    assert decrypted.plaintext == plaintext
    assert decrypted.key_id is not None and decrypted.key_id.endswith(key_id)


async def test_decrypt_with_wrong_encryption_context_is_rejected(
    kms: AsyncKMSClient, key_id: str
) -> None:
    """Verifies decrypting under a different encryption context raises InvalidCiphertextException."""
    encrypted = await kms.encrypt(
        EncryptInput(
            key_id=key_id, plaintext=b"secret", encryption_context={"purpose": "a"}
        )
    )
    assert encrypted.ciphertext_blob is not None

    with pytest.raises(InvalidCiphertextException):
        await kms.decrypt(
            DecryptInput(
                ciphertext_blob=encrypted.ciphertext_blob,
                encryption_context={"purpose": "b"},
            )
        )


async def test_alias_lifecycle_resolves_to_key(
    kms: AsyncKMSClient, key_id: str
) -> None:
    """Verifies a created alias is listed for its key, usable in place of the key ID, and then removed."""
    alias = unique_alias_name()
    await kms.create_alias(CreateAliasInput(alias_name=alias, target_key_id=key_id))
    try:
        via_alias = await wait_until(
            lambda: kms.describe_key(DescribeKeyInput(key_id=alias)),
            retry_on=(NotFoundException,),
        )
        listed = await wait_until(
            lambda: kms.list_aliases(ListAliasesInput(key_id=key_id)),
            done=lambda r: alias in [e.alias_name for e in r.aliases or []],
        )
        entries = [entry for entry in listed.aliases or [] if entry.alias_name == alias]
        assert len(entries) == 1
        assert entries[0].target_key_id == key_id

        assert via_alias.key_metadata is not None
        assert via_alias.key_metadata.key_id == key_id

        encrypted = await wait_until(
            lambda: kms.encrypt(EncryptInput(key_id=alias, plaintext=b"via alias")),
            retry_on=(NotFoundException,),
        )
        assert encrypted.key_id is not None and encrypted.key_id.endswith(key_id)
    finally:
        await kms.delete_alias(DeleteAliasInput(alias_name=alias))

    await wait_until_gone(
        lambda: kms.describe_key(DescribeKeyInput(key_id=alias)),
        gone_on=(NotFoundException,),
    )
    await wait_until(
        lambda: kms.list_aliases(ListAliasesInput(key_id=key_id)),
        done=lambda listed: alias not in [e.alias_name for e in listed.aliases or []],
    )
