#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from aws_credentials_sts.resolvers import (
    AssumeRoleConfigurationError,
    AssumeRoleCredentialsResolver,
    ProfileAssumeRoleCredentialsResolver,
    _account_id_from_arn,
    _resolve_sts_region,
)
from aws_sdk_sts.models import (
    AssumedRoleUser,
    AssumeRoleOutput,
    Credentials,
)
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import (
    AWSCredentialsIdentity,
    StaticCredentialsResolver,
)
from smithy_aws_core.identity.chain import (
    ChainSetup,
    Standard,
    StandardProvider,
)
from smithy_aws_core.identity.chain.provider import NamedResolver
from smithy_core.exceptions import SmithyIdentityError

ROLE_ARN = "arn:aws:iam::123456789012:role/MyRole"
SOURCE_ROLE_ARN = "arn:aws:iam::123456789012:role/SourceRole"
ASSUMED_ROLE_ARN = "arn:aws:sts::123456789012:assumed-role/MyRole/session"
ACCESS_KEY_ID = "test-access-key"
SECRET_ACCESS_KEY = "test-secret-key"
SESSION_TOKEN = "test-session-token"


class _FakeProvider:
    """A chain provider that adds a single static resolver during setup."""

    def __init__(self, resolver: StaticCredentialsResolver) -> None:
        self._resolver = resolver

    @property
    def name(self) -> str:
        return StandardProvider.ENVIRONMENT.canonical_name

    @property
    def ordering(self) -> Standard:
        return Standard(slot=StandardProvider.ENVIRONMENT)

    async def setup(self, identity_type: object, setup: ChainSetup) -> None:
        setup.add_resolver(self._resolver)


@pytest.fixture
def merged_config() -> Callable[..., MergedConfig]:
    def _build(profiles: Mapping[str, Mapping[str, str]]) -> MergedConfig:
        sections = {
            name: Section(properties=dict(properties))
            for name, properties in profiles.items()
        }
        return MergedConfig(StandardizedOutput(profiles=sections), StandardizedOutput())

    return _build


def _future_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def _past_expiry() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


def _valid_output(
    *, access_key_id: str = ACCESS_KEY_ID, expiration: datetime | None = None
) -> AssumeRoleOutput:
    """An AssumeRole response with valid credentials and assumed-role user."""
    return AssumeRoleOutput(
        credentials=Credentials(
            access_key_id=access_key_id,
            secret_access_key=SECRET_ACCESS_KEY,
            session_token=SESSION_TOKEN,
            expiration=expiration or _future_expiry(),
        ),
        assumed_role_user=AssumedRoleUser(assumed_role_id="id", arn=ASSUMED_ROLE_ARN),
    )


def _mock_sts_client(
    resolver: AssumeRoleCredentialsResolver, *responses: AssumeRoleOutput
) -> AsyncMock:
    """Attach a mock STS client returning one response per AssumeRole call."""
    client = AsyncMock()
    client.assume_role.side_effect = list(responses)
    resolver._client = client
    return client


@pytest.mark.parametrize(
    ("env_aws_region", "env_aws_default_region", "profile_region", "expected"),
    [
        (None, None, None, "us-east-1"),
        ("us-west-2", None, "eu-west-1", "us-west-2"),
        (None, "ap-south-1", None, "ap-south-1"),
        (None, None, "eu-west-1", "eu-west-1"),
    ],
)
def test_resolve_sts_region(
    env_aws_region: str | None,
    env_aws_default_region: str | None,
    profile_region: str | None,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    merged_config: Callable[..., MergedConfig],
) -> None:
    for name, value in (
        ("AWS_REGION", env_aws_region),
        ("AWS_DEFAULT_REGION", env_aws_default_region),
    ):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)

    config_file = merged_config(
        {"default": {"region": profile_region}} if profile_region else {}
    )

    region = _resolve_sts_region(config_file=config_file, profile_name="default")

    assert region == expected


@pytest.mark.parametrize(
    "arn,expected",
    [
        (ASSUMED_ROLE_ARN, "123456789012"),
        ("arn:aws:sts:::assumed-role/MyRole/session", None),  # empty account field
        ("not-an-arn", None),  # too few segments
        (None, None),
    ],
)
def test_account_id_from_arn(arn: str | None, expected: str | None) -> None:
    assert _account_id_from_arn(arn) == expected


# ---------------------------------------------------------------------------
# AssumeRoleCredentialsResolver
# ---------------------------------------------------------------------------


async def test_resolves_identity_from_assume_role() -> None:
    expiration = _future_expiry()
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    _mock_sts_client(resolver, _valid_output(expiration=expiration))

    identity = await resolver.get_identity(properties={})

    assert identity.access_key_id == ACCESS_KEY_ID
    assert identity.secret_access_key == SECRET_ACCESS_KEY
    assert identity.session_token == SESSION_TOKEN
    assert identity.expiration == expiration
    assert identity.account_id == "123456789012"


async def test_missing_credentials_raises() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    _mock_sts_client(resolver, AssumeRoleOutput(credentials=None))

    with pytest.raises(SmithyIdentityError, match="did not contain credentials"):
        await resolver.get_identity(properties={})


async def test_valid_credentials_reused() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    sts_client = _mock_sts_client(
        resolver,
        _valid_output(access_key_id="test-access-key-1"),
        _valid_output(access_key_id="test-access-key-2"),
    )

    identity_one = await resolver.get_identity(properties={})
    identity_two = await resolver.get_identity(properties={})

    # The cached identity is returned without a second STS call.
    assert identity_one is identity_two
    assert sts_client.assume_role.call_count == 1


async def test_expired_credentials_refreshed() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    sts_client = _mock_sts_client(
        resolver,
        _valid_output(access_key_id="test-access-key-1", expiration=_past_expiry()),
        _valid_output(access_key_id="test-access-key-2"),
    )

    identity_one = await resolver.get_identity(properties={})
    identity_two = await resolver.get_identity(properties={})

    # The cached identity is refreshed with a second STS call.
    assert identity_one is not identity_two
    assert identity_one.access_key_id == "test-access-key-1"
    assert identity_two.access_key_id == "test-access-key-2"
    assert sts_client.assume_role.call_count == 2


async def test_assume_role_request_uses_role_arn() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(),
        role_arn=ROLE_ARN,
        role_session_name="test-session-name",
    )
    sts_client = _mock_sts_client(resolver, _valid_output())

    await resolver.get_identity(properties={})

    request = sts_client.assume_role.call_args.kwargs
    assert request["role_arn"] == ROLE_ARN
    assert request["role_session_name"] == "test-session-name"


async def test_assume_role_request_forwards_external_id() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(),
        role_arn=ROLE_ARN,
        external_id="my-external-id",
    )
    sts_client = _mock_sts_client(resolver, _valid_output())

    await resolver.get_identity(properties={})

    request = sts_client.assume_role.call_args.kwargs
    assert request["external_id"] == "my-external-id"


async def test_assume_role_request_forwards_duration_seconds() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(),
        role_arn=ROLE_ARN,
        duration_seconds=3600,
    )
    sts_client = _mock_sts_client(resolver, _valid_output())

    await resolver.get_identity(properties={})

    request = sts_client.assume_role.call_args.kwargs
    assert request["duration_seconds"] == 3600


async def test_role_session_name_generated_when_unset() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    sts_client = _mock_sts_client(resolver, _valid_output())

    await resolver.get_identity(properties={})

    request = sts_client.assume_role.call_args.kwargs
    assert request["role_session_name"].startswith("aws-sdk-python-")


async def test_role_session_name_stable_across_refreshes() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncMock(), role_arn=ROLE_ARN
    )
    sts_client = _mock_sts_client(
        resolver,
        _valid_output(expiration=_past_expiry()),
        _valid_output(),
    )

    await resolver.get_identity(properties={})
    await resolver.get_identity(properties={})

    first, second = sts_client.assume_role.call_args_list
    assert first.kwargs["role_session_name"] == second.kwargs["role_session_name"]


# ---------------------------------------------------------------------------
# ProfileAssumeRoleCredentialsResolver
# ---------------------------------------------------------------------------


def test_missing_profile_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"default": {"region": "us-east-1"}})

    with pytest.raises(
        AssumeRoleConfigurationError, match="Profile 'missing' does not exist"
    ):
        ProfileAssumeRoleCredentialsResolver(
            profile_name="missing", config_file=config_file
        )


async def test_source_profile_with_static_credentials(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "base"},
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert isinstance(delegate, AssumeRoleCredentialsResolver)
    assert delegate._role_arn == ROLE_ARN
    assert isinstance(delegate._source_resolver, StaticCredentialsResolver)
    identity = await delegate._source_resolver.get_identity(properties={})
    assert identity.access_key_id == "akid"
    assert identity.secret_access_key == "secret"


async def test_profile_duration_seconds_forwarded_to_delegate(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {
                "role_arn": ROLE_ARN,
                "source_profile": "base",
                "duration_seconds": "43200",
            },
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert delegate._duration_seconds == 43200


async def test_profile_invalid_duration_seconds_ignored(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {
                "role_arn": ROLE_ARN,
                "source_profile": "base",
                "duration_seconds": "not-a-number",
            },
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert delegate._duration_seconds is None


async def test_first_profile_credentials_ignored_in_favor_of_source(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {
                "role_arn": ROLE_ARN,
                "source_profile": "base",
                "aws_access_key_id": "ignored-akid",
                "aws_secret_access_key": "ignored-secret",
            },
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert isinstance(delegate._source_resolver, StaticCredentialsResolver)
    identity = await delegate._source_resolver.get_identity(properties={})
    assert identity.access_key_id == "akid"
    assert identity.secret_access_key == "secret"


async def test_nested_source_profile_role_chain(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "intermediate"},
            "intermediate": {
                "role_arn": SOURCE_ROLE_ARN,
                "source_profile": "base",
            },
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    # The outer role assumes via an inner AssumeRole resolver that itself
    # sources from the static base profile.
    assert isinstance(delegate, AssumeRoleCredentialsResolver)
    inner = delegate._source_resolver
    assert isinstance(inner, AssumeRoleCredentialsResolver)
    assert inner._role_arn == SOURCE_ROLE_ARN
    assert isinstance(inner._source_resolver, StaticCredentialsResolver)


async def test_chain_terminates_at_static_credentials(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "middle"},
            "middle": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
                "role_arn": SOURCE_ROLE_ARN,
                "source_profile": "base",
            },
            "base": {
                "aws_access_key_id": "unused-akid",
                "aws_secret_access_key": "unused-secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert delegate._role_arn == ROLE_ARN
    assert isinstance(delegate._source_resolver, StaticCredentialsResolver)
    identity = await delegate._source_resolver.get_identity(properties={})
    assert identity.access_key_id == "akid"
    assert identity.secret_access_key == "secret"


async def test_missing_source_profile_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "source_profile": "ghost"}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError, match="Source profile 'ghost' does not exist"
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_source_profile_without_credentials_or_role_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "base"},
            "base": {"region": "us-east-1"},
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Source profile 'base' has no supported credential source",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_circular_source_profile_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "a": {"role_arn": ROLE_ARN, "source_profile": "b"},
            "b": {"role_arn": SOURCE_ROLE_ARN, "source_profile": "a"},
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="a", config_file=config_file
    )

    with pytest.raises(AssumeRoleConfigurationError, match="Circular"):
        await resolver._create_assume_role_resolver(profile_name="a", visited=("a",))


async def test_circular_source_profile_with_static_credentials_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "a": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
                "role_arn": ROLE_ARN,
                "source_profile": "b",
            },
            "b": {"role_arn": SOURCE_ROLE_ARN, "source_profile": "a"},
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="a", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Circular source_profile reference: a -> b -> a",
    ):
        await resolver._create_assume_role_resolver(profile_name="a", visited=("a",))


async def test_self_referencing_profile_requires_static_credentials(
    merged_config: Callable[..., MergedConfig],
) -> None:
    # A profile whose source_profile points at itself but has no static keys.
    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "source_profile": "role"}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Self-referencing profile 'role' must contain complete static credentials",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_self_referencing_profile_with_static_credentials(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {
                "role_arn": ROLE_ARN,
                "source_profile": "role",
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            }
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert isinstance(delegate._source_resolver, StaticCredentialsResolver)


async def test_missing_role_arn_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"role": {"source_profile": "base"}})
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError, match="Profile 'role' does not define role_arn"
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_both_source_and_credential_source_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {
                "role_arn": ROLE_ARN,
                "source_profile": "base",
                "credential_source": "Environment",
            }
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Profile 'role' cannot define both 'source_profile' and 'credential_source'",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_neither_source_nor_credential_source_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config({"role": {"role_arn": ROLE_ARN}})
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Profile 'role' must define either 'source_profile' or 'credential_source'",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_partial_static_credentials_raise(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "base"},
            "base": {"aws_access_key_id": "akid"},
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Profile 'base' contains partial credentials",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_unsupported_credential_source_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "credential_source": "ProfileSso"}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="Unsupported 'credential_source': 'ProfileSso'",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


@pytest.mark.parametrize(
    "credential_source",
    ["Environment", "EcsContainer", "Ec2InstanceMetadata"],
)
async def test_credential_source_builds_resolver_from_provider(
    merged_config: Callable[..., MergedConfig],
    credential_source: str,
) -> None:
    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "credential_source": credential_source}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )
    static = StaticCredentialsResolver(
        AWSCredentialsIdentity(access_key_id="akid", secret_access_key="secret")
    )
    resolver._find_provider = lambda slot: _FakeProvider(static)  # type: ignore[assignment]

    delegate = await resolver._create_assume_role_resolver(
        profile_name="role", visited=("role",)
    )

    assert isinstance(delegate, AssumeRoleCredentialsResolver)
    assert isinstance(delegate._source_resolver, NamedResolver)
    assert delegate._source_resolver.resolver is static


async def test_credential_source_no_installed_provider_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "credential_source": "Ec2InstanceMetadata"}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )
    resolver._find_provider = lambda slot: None  # type: ignore[assignment]

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="No provider is installed for credential source 'Ec2InstanceMetadata'",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_credential_source_provider_registers_nothing_raises(
    merged_config: Callable[..., MergedConfig],
) -> None:
    class _EmptyProvider:
        async def setup(self, identity_type: object, setup: ChainSetup) -> None:
            return None

    config_file = merged_config(
        {"role": {"role_arn": ROLE_ARN, "credential_source": "Environment"}}
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )
    resolver._find_provider = lambda slot: _EmptyProvider()  # type: ignore[assignment]

    with pytest.raises(
        AssumeRoleConfigurationError,
        match="'Environment' credential source is not configured",
    ):
        await resolver._create_assume_role_resolver(
            profile_name="role", visited=("role",)
        )


async def test_get_identity_creates_and_reuses_delegate(
    merged_config: Callable[..., MergedConfig],
) -> None:
    config_file = merged_config(
        {
            "role": {"role_arn": ROLE_ARN, "source_profile": "base"},
            "base": {
                "aws_access_key_id": "akid",
                "aws_secret_access_key": "secret",
            },
        }
    )
    resolver = ProfileAssumeRoleCredentialsResolver(
        profile_name="role", config_file=config_file
    )
    expected = AWSCredentialsIdentity(access_key_id="a", secret_access_key="s")
    delegate = AsyncMock()
    delegate.get_identity.return_value = expected

    resolver._create_assume_role_resolver = AsyncMock()
    resolver._create_assume_role_resolver.return_value = delegate

    first = await resolver.get_identity(properties={})
    second = await resolver.get_identity(properties={})

    assert first is expected
    assert second is expected
    # The delegate is built once and reused across calls.
    assert resolver._delegate is delegate
    assert delegate.get_identity.await_count == 2
