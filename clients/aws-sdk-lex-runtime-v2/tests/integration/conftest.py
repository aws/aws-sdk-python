# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest fixtures for Lex Runtime V2 integration tests.

Creates and tears down a Lex V2 bot with a Greeting intent once per
test session. All integration tests receive the bot_id via the
``lex_bot`` fixture.
"""

import json
import uuid
from typing import Any

import boto3
import pytest

from . import LOCALE_ID, REGION

# Tags applied to all resources so orphaned resources from interrupted
# test runs can be discovered and cleaned up.
_TAGS = [{"Key": "Purpose", "Value": "IntegTest"}]


def _create_lex_bot(
    iam_client: Any, lex_client: Any, sts_client: Any, role_name: str, bot_name: str
) -> str:
    """Create a Lex V2 bot with a Greeting intent.

    Args:
        iam_client: A boto3 IAM client.
        lex_client: A boto3 lexv2-models client.
        sts_client: A boto3 STS client.
        role_name: The name of the IAM role to create for the bot.
        bot_name: The name of the Lex bot to create.

    Returns:
        The bot ID.
    """
    account_id = sts_client.get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    # Create IAM role for the bot
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lexv2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Tags=_TAGS,
    )

    # Create bot
    response = lex_client.create_bot(
        botName=bot_name,
        roleArn=role_arn,
        dataPrivacy={"childDirected": False},
        # 5-minute idle timeout is sufficient for integration tests.
        idleSessionTTLInSeconds=300,
        botTags={t["Key"]: t["Value"] for t in _TAGS},
    )
    bot_id = response["botId"]
    lex_client.get_waiter("bot_available").wait(botId=bot_id)

    # Create locale
    lex_client.create_bot_locale(
        botId=bot_id,
        botVersion="DRAFT",
        localeId=LOCALE_ID,
        # Required field. Confidence threshold (0-1) that determines when Lex
        # inserts AMAZON.FallbackIntent into the interpretations list.
        # 0.40 is a reasonable value for a simple test bot.
        nluIntentConfidenceThreshold=0.40,
    )
    lex_client.get_waiter("bot_locale_created").wait(
        botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID
    )

    # Create intent
    lex_client.create_intent(
        intentName="Greeting",
        botId=bot_id,
        botVersion="DRAFT",
        localeId=LOCALE_ID,
        sampleUtterances=[
            {"utterance": "Hello"},
            {"utterance": "Hi"},
            {"utterance": "Hey"},
        ],
        intentClosingSetting={
            "closingResponse": {
                "messageGroups": [
                    {
                        "message": {
                            "plainTextMessage": {"value": "Hello! How can I help you?"}
                        }
                    }
                ]
            },
            "active": True,
        },
    )

    # Build locale
    lex_client.build_bot_locale(botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID)
    lex_client.get_waiter("bot_locale_built").wait(
        botId=bot_id, botVersion="DRAFT", localeId=LOCALE_ID
    )

    return bot_id


def _delete_lex_bot(
    iam_client: Any, lex_client: Any, role_name: str, bot_id: str | None
) -> None:
    """Delete a Lex V2 bot and its associated IAM role.

    Args:
        iam_client: A boto3 IAM client.
        lex_client: A boto3 lexv2-models client.
        role_name: The name of the IAM role to delete.
        bot_id: The bot ID to delete, or None if creation failed.
    """
    if bot_id:
        lex_client.delete_bot(botId=bot_id, skipResourceInUseCheck=True)

    try:
        iam_client.delete_role(RoleName=role_name)
    except iam_client.exceptions.NoSuchEntityException:
        pass


@pytest.fixture(scope="session")
def lex_bot():
    """Create a Lex bot for the test session and delete it after."""
    unique_suffix = uuid.uuid4().hex[:16]
    role_name = f"integ-test-lex-runtime-v2-role-{unique_suffix}"
    bot_name = f"integ-test-lex-runtime-v2-bot-{unique_suffix}"

    iam_client = boto3.client("iam")  # pyright: ignore[reportUnknownMemberType]
    lex_client = boto3.client("lexv2-models", region_name=REGION)  # pyright: ignore[reportUnknownMemberType]
    sts_client = boto3.client("sts")  # pyright: ignore[reportUnknownMemberType]

    bot_id = None
    try:
        bot_id = _create_lex_bot(
            iam_client, lex_client, sts_client, role_name, bot_name
        )
        yield bot_id
    finally:
        _delete_lex_bot(iam_client, lex_client, role_name, bot_id)
