#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

# pyright: reportPrivateUsage=false
import asyncio
import os
import re
import time
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Literal
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from aws_credentials_sts import (
    ProfileWebIdentityProvider,
    WebIdentityConfigurationError,
    WebIdentityCredentialsResolver,
    WebIdentityTokenEnvProvider,
)
from aws_credentials_sts._web_identity import read_token
from aws_credentials_sts.aio import (
    AsyncProfileWebIdentityProvider,
    AsyncWebIdentityCredentialsResolver,
    AsyncWebIdentityTokenEnvProvider,
)
from aws_sdk_sts.models import (
    AssumedRoleUser,
    AssumeRoleWithWebIdentityInput,
    AssumeRoleWithWebIdentityOutput,
    Credentials,
    ExpiredTokenException,
    IDPCommunicationErrorException,
    InvalidIdentityTokenException,
)
from smithy_aws_core.aio.identity import AsyncIdentityChain
from smithy_aws_core.aio.identity.chain.provider import AsyncChainSetup
from smithy_aws_core.config.file_parser import Section, StandardizedOutput
from smithy_aws_core.config.merged_config import MergedConfig
from smithy_aws_core.identity import AWSCredentialsIdentity
from smithy_aws_core.identity.chain.provider import ChainSetup
from smithy_aws_core.identity.chain.resolver import IdentityChain
from smithy_core.exceptions import SmithyIdentityError
from smithy_http.aio.aiohttp import AIOHTTPClient
from smithy_http.aio.testing import AsyncMockHTTPClient
from smithy_http.testing import MockHTTPClient

ROLE_ARN = "arn:aws:iam::123456789012:role/WebIdentityRole"
ASSUMED_ROLE_ARN = "arn:aws:sts::123456789012:assumed-role/WebIdentityRole/session"
ACCESS_KEY_ID = "test-access-key"
SECRET_ACCESS_KEY = "test-secret-key"
SESSION_TOKEN = "test-session-token"

type Mode = Literal["sync", "async"]
type Resolver = WebIdentityCredentialsResolver | AsyncWebIdentityCredentialsResolver
type Outcome = AssumeRoleWithWebIdentityOutput | Exception


def _output(
    *, access_key_id: str = ACCESS_KEY_ID, expiration: datetime | None = None
) -> AssumeRoleWithWebIdentityOutput:
    """An AssumeRoleWithWebIdentity response with valid credentials."""
    return AssumeRoleWithWebIdentityOutput(
        credentials=Credentials(
            access_key_id=access_key_id,
            secret_access_key=SECRET_ACCESS_KEY,
            session_token=SESSION_TOKEN,
            expiration=expiration or datetime.now(UTC) + timedelta(hours=1),
        ),
        assumed_role_user=AssumedRoleUser(assumed_role_id="id", arn=ASSUMED_ROLE_ARN),
    )


class _FakeSTS:
    """Plays back scripted STS outcomes and records each request.

    After every call it writes a new token to the token file, so a test can tell
    from the recorded tokens whether the resolver read the file again.
    """

    def __init__(self, token_file: Path, *outcomes: Outcome) -> None:
        self._token_file = token_file
        self._outcomes = list(outcomes)
        self.requests: list[AssumeRoleWithWebIdentityInput] = []

    @property
    def tokens(self) -> list[str | None]:
        return [request.web_identity_token for request in self.requests]

    def __call__(
        self, request: AssumeRoleWithWebIdentityInput
    ) -> AssumeRoleWithWebIdentityOutput:
        self.requests.append(request)
        self._token_file.write_text(f"token-{len(self.requests) + 1}")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _resolver(mode: Mode, token_file: Path, sts: Any = None, **kwargs: Any) -> Resolver:
    """Create a resolver in the given mode, with ``sts`` standing in for STS."""
    resolver_class = (
        WebIdentityCredentialsResolver
        if mode == "sync"
        else AsyncWebIdentityCredentialsResolver
    )
    resolver = resolver_class(
        role_arn=ROLE_ARN, web_identity_token_file=token_file, **kwargs
    )
    resolver._backoff = Mock(compute_next_backoff_delay=Mock(return_value=0))
    if sts is not None:
        client = Mock() if mode == "sync" else AsyncMock()
        client.assume_role_with_web_identity.side_effect = sts
        resolver._client = client
    return resolver


async def _get_identity(resolver: Resolver) -> AWSCredentialsIdentity:
    if isinstance(resolver, AsyncWebIdentityCredentialsResolver):
        return await resolver.get_identity(properties={})
    return resolver.get_identity(properties={})


async def _invalidate(resolver: Resolver) -> None:
    if isinstance(resolver, AsyncWebIdentityCredentialsResolver):
        await resolver.invalidate()
    else:
        resolver.invalidate()


@contextmanager
def _patched_client_class(mode: Mode, sts: _FakeSTS) -> Iterator[MagicMock]:
    """Replace the STS client class so the resolver creates a fake client.

    The fake works whether the resolver keeps the client or uses it in a ``with``
    block.
    """
    target = (
        "aws_sdk_sts.client.STSClient"
        if mode == "sync"
        else "aws_sdk_sts.aio.client.AsyncSTSClient"
    )
    with patch(target) as client_class:
        client = client_class.return_value
        mock_class = Mock if mode == "sync" else AsyncMock
        client.assume_role_with_web_identity = mock_class(side_effect=sts)
        enter = "__enter__" if mode == "sync" else "__aenter__"
        getattr(client, enter).return_value = client
        yield client_class


@pytest.fixture(autouse=True)
def isolated_aws_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the machine's AWS environment and config files out of every test."""
    for name in [name for name in os.environ if name.startswith("AWS_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "missing-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "missing-creds"))


@pytest.fixture(params=["sync", "async"])
def mode(request: pytest.FixtureRequest) -> Mode:
    return request.param


@pytest.fixture
def token_file(tmp_path: Path) -> Path:
    path = tmp_path / "token"
    path.write_text("token-1")
    return path


@pytest.fixture
def merged_config() -> Callable[..., MergedConfig]:
    def _build(profiles: Mapping[str, Mapping[str, str]]) -> MergedConfig:
        sections = {
            name: Section(properties=dict(properties))
            for name, properties in profiles.items()
        }
        return MergedConfig(StandardizedOutput(profiles=sections), StandardizedOutput())

    return _build


# ---------------------------------------------------------------------------
# Resolvers tests
# ---------------------------------------------------------------------------


async def test_requests_credentials_for_configured_role(
    mode: Mode, token_file: Path
) -> None:
    token_file.write_text("  token-1\n")
    sts = _FakeSTS(token_file, _output())
    resolver = _resolver(mode, token_file, sts, role_session_name="my-session")

    identity = await _get_identity(resolver)

    request = sts.requests[0]
    assert request.role_arn == ROLE_ARN
    assert request.role_session_name == "my-session"
    # Whitespace around the token, such as a trailing newline, isn't sent.
    assert request.web_identity_token == "token-1"
    assert identity.access_key_id == ACCESS_KEY_ID
    assert identity.secret_access_key == SECRET_ACCESS_KEY
    assert identity.session_token == SESSION_TOKEN
    assert identity.expiration is not None
    assert identity.account_id == "123456789012"


def test_default_session_name_is_shared_and_valid(token_file: Path) -> None:
    sync_resolver = _resolver("sync", token_file)
    async_resolver = _resolver("async", token_file)

    name = sync_resolver._role_session_name
    # Every resolver in the process uses the same generated name.
    assert async_resolver._role_session_name == name
    # The name meets STS's RoleSessionName constraints.
    assert 2 <= len(name) <= 64
    assert re.fullmatch(r"[\w+=,.@-]+", name)


async def test_response_without_credentials_raises(token_file: Path) -> None:
    sts = _FakeSTS(token_file, AssumeRoleWithWebIdentityOutput())
    resolver = _resolver("sync", token_file, sts)

    with pytest.raises(SmithyIdentityError, match="did not contain credentials"):
        await _get_identity(resolver)


@pytest.mark.parametrize(
    ("outcomes", "expected_error", "expected_tokens"),
    [
        pytest.param(
            [ExpiredTokenException(message="expired"), _output()],
            None,
            ["token-1", "token-2"],
            id="expired-token-retries-with-new-token",
        ),
        pytest.param(
            [IDPCommunicationErrorException(message="idp down"), _output()],
            None,
            ["token-1", "token-1"],
            id="idp-error-retries-with-same-token",
        ),
        pytest.param(
            [ExpiredTokenException(message="expired")] * 4,
            ExpiredTokenException,
            ["token-1", "token-2", "token-3", "token-4"],
            id="expired-token-gives-up-after-retries",
        ),
        pytest.param(
            [IDPCommunicationErrorException(message="idp down")] * 4,
            IDPCommunicationErrorException,
            ["token-1"] * 4,
            id="idp-error-gives-up-after-retries",
        ),
        pytest.param(
            [InvalidIdentityTokenException(message="invalid")],
            InvalidIdentityTokenException,
            ["token-1"],
            id="other-sts-error-not-retried",
        ),
        pytest.param(
            [ConnectionError("network down")],
            ConnectionError,
            ["token-1"],
            id="network-error-not-retried",
        ),
    ],
)
async def test_retries_sts_errors(
    mode: Mode,
    token_file: Path,
    outcomes: list[Outcome],
    expected_error: type[Exception] | None,
    expected_tokens: list[str],
) -> None:
    sts = _FakeSTS(token_file, *outcomes)
    resolver = _resolver(mode, token_file, sts)

    if expected_error is None:
        await _get_identity(resolver)
    else:
        with pytest.raises(expected_error):
            await _get_identity(resolver)

    assert sts.tokens == expected_tokens


@pytest.mark.parametrize("fixed_before_retry", [True, False])
@pytest.mark.parametrize(
    "initial_content",
    # A missing file, a non-ASCII file (a UTF-8 byte order mark), and an empty one.
    [None, b"\xef\xbb\xbftoken-1", b"\n"],
    ids=["missing", "non-ascii", "empty"],
)
async def test_retries_unreadable_token_file(
    mode: Mode,
    tmp_path: Path,
    initial_content: bytes | None,
    fixed_before_retry: bool,
) -> None:
    token_file = tmp_path / "token"
    if initial_content is not None:
        token_file.write_bytes(initial_content)
    sts = _FakeSTS(token_file, _output())
    resolver = _resolver(mode, token_file, sts)

    def fix_file_before_retry(retry_attempt: int) -> float:
        if fixed_before_retry:
            token_file.write_text("token-1")
        return 0

    backoff = Mock(side_effect=fix_file_before_retry)
    resolver._backoff = Mock(compute_next_backoff_delay=backoff)

    if fixed_before_retry:
        await _get_identity(resolver)
        assert sts.tokens == ["token-1"]
    else:
        with pytest.raises(SmithyIdentityError, match="web identity token file"):
            await _get_identity(resolver)
        assert sts.requests == []
        # The file was read on every attempt: once, then on each of 3 retries.
        assert backoff.call_count == 3


@pytest.mark.parametrize(
    ("expires_in", "expected_sts_calls"),
    [(timedelta(hours=1), 1), (timedelta(hours=-1), 2)],
    ids=["valid-credentials-cached", "expired-credentials-refreshed"],
)
async def test_caches_credentials_until_expired(
    mode: Mode, token_file: Path, expires_in: timedelta, expected_sts_calls: int
) -> None:
    expiration = datetime.now(UTC) + expires_in
    sts = _FakeSTS(
        token_file, _output(expiration=expiration), _output(expiration=expiration)
    )
    resolver = _resolver(mode, token_file, sts)

    await _get_identity(resolver)
    await _get_identity(resolver)

    assert len(sts.requests) == expected_sts_calls


async def test_invalidate_forces_refresh(mode: Mode, token_file: Path) -> None:
    sts = _FakeSTS(
        token_file,
        _output(access_key_id="test-access-key-1"),
        _output(access_key_id="test-access-key-2"),
    )
    resolver = _resolver(mode, token_file, sts)

    await _get_identity(resolver)
    await _invalidate(resolver)
    identity = await _get_identity(resolver)

    assert identity.access_key_id == "test-access-key-2"
    assert len(sts.requests) == 2


async def test_closes_sts_client_it_creates(
    mode: Mode, token_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    sts = _FakeSTS(token_file, _output())
    resolver = _resolver(mode, token_file)

    with _patched_client_class(mode, sts) as client_class:
        await _get_identity(resolver)

    exit_method = "__exit__" if mode == "sync" else "__aexit__"
    getattr(client_class.return_value, exit_method).assert_called_once()
    config = client_class.call_args.kwargs["config"]
    # Without an explicit region, the region comes from the environment.
    assert config.region == "us-west-2"

    # The fake client didn't close the real transport the config created.
    if mode == "sync":
        config.transport.close()
    else:
        await config.transport.close()


async def test_closes_transport_when_token_never_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aws_sdk_sts.aio.config import AsyncSTSConfig

    configs: list[AsyncSTSConfig] = []
    resolve = AsyncSTSConfig.resolve

    async def recording_resolve(**kwargs: Any) -> AsyncSTSConfig:
        config = await resolve(**kwargs)
        configs.append(config)
        return config

    monkeypatch.setattr(AsyncSTSConfig, "resolve", recording_resolve)
    resolver = _resolver("async", tmp_path / "missing-token")

    with pytest.raises(SmithyIdentityError, match="web identity token file"):
        await _get_identity(resolver)

    # No request was sent, so the client never closed the transport itself.
    assert len(configs) == 1
    transport = configs[0].transport
    assert isinstance(transport, AIOHTTPClient)
    assert transport._closed


async def test_reuses_sts_client_for_callers_http_client(
    mode: Mode, token_file: Path
) -> None:
    http_client = Mock()
    # The first credentials are already expired, so the second call refreshes them
    # and shows the same client is reused across refreshes.
    sts = _FakeSTS(token_file, _output(expiration=datetime.now(UTC)), _output())
    resolver = _resolver(mode, token_file, region="eu-west-1", http_client=http_client)

    with _patched_client_class(mode, sts) as client_class:
        await _get_identity(resolver)
        await _get_identity(resolver)

    # The client is created once and never closed, since that would close the
    # caller's HTTP client.
    client_class.assert_called_once()
    exit_method = "__exit__" if mode == "sync" else "__aexit__"
    getattr(client_class.return_value, exit_method).assert_not_called()
    config = client_class.call_args.kwargs["config"]
    assert config.region == "eu-west-1"
    assert config.transport is http_client


def test_returns_cached_credentials_when_invalidated_concurrently(
    token_file: Path,
) -> None:
    resolver = _resolver("sync", token_file)
    assert isinstance(resolver, WebIdentityCredentialsResolver)

    class InvalidatedWhileChecked(AWSCredentialsIdentity):
        @property
        def is_expired(self) -> bool:
            # Another thread invalidates the cache while this thread checks it.
            resolver._credentials = None
            return False

    cached = InvalidatedWhileChecked(
        access_key_id=ACCESS_KEY_ID, secret_access_key=SECRET_ACCESS_KEY
    )
    resolver._credentials = cached

    assert resolver.get_identity(properties={}) is cached


def test_concurrent_threads_share_one_refresh(token_file: Path) -> None:
    fake_sts = _FakeSTS(token_file, _output())

    def slow_sts(
        request: AssumeRoleWithWebIdentityInput,
    ) -> AssumeRoleWithWebIdentityOutput:
        time.sleep(0.05)  # Keep the refresh in flight while other threads arrive.
        return fake_sts(request)

    resolver = _resolver("sync", token_file, slow_sts)
    assert isinstance(resolver, WebIdentityCredentialsResolver)
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(resolver.get_identity, properties={}) for _ in range(10)]
    # result() re-raises any error a thread hit, so a failing thread fails the test.
    identities = [future.result() for future in futures]

    assert len(fake_sts.requests) == 1
    assert all(identity is identities[0] for identity in identities)


async def test_concurrent_tasks_share_one_refresh(token_file: Path) -> None:
    fake_sts = _FakeSTS(token_file, _output())

    async def slow_sts(
        request: AssumeRoleWithWebIdentityInput,
    ) -> AssumeRoleWithWebIdentityOutput:
        await asyncio.sleep(0.05)  # Keep the refresh in flight while others arrive.
        return fake_sts(request)

    resolver = _resolver("async", token_file, slow_sts)

    identities = await asyncio.gather(*(_get_identity(resolver) for _ in range(10)))

    assert len(fake_sts.requests) == 1
    assert all(identity is identities[0] for identity in identities)


async def test_token_read_does_not_block_event_loop(
    token_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def slow_read_token(path: Path, *, is_last_attempt: bool) -> str | None:
        time.sleep(0.3)  # A slow disk.
        return read_token(path, is_last_attempt=is_last_attempt)

    monkeypatch.setattr("aws_credentials_sts.aio.resolvers.read_token", slow_read_token)
    resolver = _resolver("async", token_file, _FakeSTS(token_file, _output()))
    ticks = 0

    async def tick() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    ticker = asyncio.create_task(tick())
    await _get_identity(resolver)
    ticker.cancel()

    # If the read blocked the loop, the ticker couldn't run while it waited.
    assert ticks >= 10


_STS_RESPONSE = f"""\
<AssumeRoleWithWebIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <AssumeRoleWithWebIdentityResult>
    <Credentials>
      <AccessKeyId>{ACCESS_KEY_ID}</AccessKeyId>
      <SecretAccessKey>{SECRET_ACCESS_KEY}</SecretAccessKey>
      <SessionToken>{SESSION_TOKEN}</SessionToken>
      <Expiration>2099-01-01T00:00:00Z</Expiration>
    </Credentials>
    <AssumedRoleUser>
      <AssumedRoleId>id</AssumedRoleId>
      <Arn>{ASSUMED_ROLE_ARN}</Arn>
    </AssumedRoleUser>
  </AssumeRoleWithWebIdentityResult>
</AssumeRoleWithWebIdentityResponse>""".encode()


async def test_default_chain_sends_unsigned_request_with_only_web_identity(
    mode: Mode, token_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only web identity is configured: no other credentials or config files.
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("AWS_ROLE_ARN", ROLE_ARN)
    monkeypatch.setenv("AWS_REGION", "us-west-2")

    # The real generated STS client sends the request through a mock transport.
    if mode == "sync":
        http_client = MockHTTPClient()
        http_client.add_response(body=_STS_RESPONSE)
        identity = IdentityChain.create(
            AWSCredentialsIdentity, http_client=http_client
        ).get_identity(properties={})
    else:
        http_client = AsyncMockHTTPClient()
        http_client.add_response(body=_STS_RESPONSE)
        chain = await AsyncIdentityChain.create(
            AWSCredentialsIdentity, http_client=http_client
        )
        identity = await chain.get_identity(properties={})

    assert identity.access_key_id == ACCESS_KEY_ID
    assert identity.account_id == "123456789012"
    assert http_client.call_count == 1
    request = http_client.captured_requests[0]
    # AssumeRoleWithWebIdentity authenticates with the token, not a signature.
    assert "Authorization" not in request.fields
    assert isinstance(request.body, BytesIO)
    assert b"Action=AssumeRoleWithWebIdentity" in request.body.getvalue()


# ---------------------------------------------------------------------------
# Providers tests
# ---------------------------------------------------------------------------


async def _setup(
    mode: Mode,
    provider_kind: Literal["env", "profile"],
    *,
    config_file: MergedConfig | None = None,
    profile_name: str | None = None,
) -> ChainSetup | AsyncChainSetup:
    """Run a web identity provider's setup and return the chain setup."""
    if mode == "sync":
        sync_setup = ChainSetup(config_file=config_file, profile_name=profile_name)
        provider = (
            WebIdentityTokenEnvProvider()
            if provider_kind == "env"
            else ProfileWebIdentityProvider()
        )
        sync_setup.set_current_provider(provider)
        provider.setup(AWSCredentialsIdentity, sync_setup)
        return sync_setup

    async_setup = AsyncChainSetup(config_file=config_file, profile_name=profile_name)
    async_provider = (
        AsyncWebIdentityTokenEnvProvider()
        if provider_kind == "env"
        else AsyncProfileWebIdentityProvider()
    )
    async_setup.set_current_provider(async_provider)
    await async_provider.setup(AWSCredentialsIdentity, async_setup)
    return async_setup


def _added_resolver(mode: Mode, setup: ChainSetup | AsyncChainSetup) -> Resolver:
    """Return the single terminal resolver the provider added."""
    assert setup.terminal
    assert len(setup.resolvers) == 1
    resolver = setup.resolvers[0].resolver
    expected_class = (
        WebIdentityCredentialsResolver
        if mode == "sync"
        else AsyncWebIdentityCredentialsResolver
    )
    assert isinstance(resolver, expected_class)
    return resolver


@pytest.fixture
def web_identity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", "/var/run/secrets/token")
    monkeypatch.setenv("AWS_ROLE_ARN", ROLE_ARN)
    monkeypatch.setenv("AWS_ROLE_SESSION_NAME", "env-session")
    monkeypatch.setenv("AWS_REGION", "us-west-2")


@pytest.mark.usefixtures("web_identity_env")
async def test_env_provider_adds_resolver(mode: Mode) -> None:
    resolver = _added_resolver(mode, await _setup(mode, "env"))

    assert resolver._role_arn == ROLE_ARN
    assert resolver._web_identity_token_file == Path("/var/run/secrets/token")
    assert resolver._role_session_name == "env-session"
    assert resolver._region == "us-west-2"


@pytest.mark.usefixtures("web_identity_env")
@pytest.mark.parametrize(
    ("unset_variable", "profile_name"),
    [
        pytest.param("AWS_WEB_IDENTITY_TOKEN_FILE", None, id="missing-token-file"),
        pytest.param("AWS_ROLE_ARN", None, id="missing-role-arn"),
        # An explicitly selected profile takes precedence over the environment.
        pytest.param(None, "dev", id="explicit-profile"),
    ],
)
async def test_env_provider_skips_incomplete_or_overridden_config(
    mode: Mode,
    monkeypatch: pytest.MonkeyPatch,
    unset_variable: str | None,
    profile_name: str | None,
) -> None:
    if unset_variable is not None:
        monkeypatch.delenv(unset_variable)

    setup = await _setup(mode, "env", profile_name=profile_name)

    assert setup.resolvers == ()
    assert not setup.terminal


async def test_profile_provider_adds_resolver(
    mode: Mode, merged_config: Callable[..., MergedConfig]
) -> None:
    config_file = merged_config(
        {
            "ci": {
                "role_arn": ROLE_ARN,
                "web_identity_token_file": "/var/run/secrets/token",
                "role_session_name": "profile-session",
                "region": "eu-west-1",
            }
        }
    )

    setup = await _setup(mode, "profile", config_file=config_file, profile_name="ci")

    resolver = _added_resolver(mode, setup)
    assert resolver._role_arn == ROLE_ARN
    assert resolver._web_identity_token_file == Path("/var/run/secrets/token")
    assert resolver._role_session_name == "profile-session"
    assert resolver._region == "eu-west-1"


@pytest.mark.parametrize(
    "profile",
    [
        pytest.param({"role_arn": ROLE_ARN}, id="no-token-file"),
        # A blank leftover key must not break a profile that resolves another way.
        pytest.param(
            {"credential_process": "get-creds", "web_identity_token_file": ""},
            id="blank-token-file",
        ),
    ],
)
async def test_profile_provider_skips_profile_without_token_file(
    mode: Mode, merged_config: Callable[..., MergedConfig], profile: dict[str, str]
) -> None:
    config_file = merged_config({"ci": profile})

    setup = await _setup(mode, "profile", config_file=config_file, profile_name="ci")

    assert setup.resolvers == ()


async def test_profile_provider_requires_role_arn(
    mode: Mode, merged_config: Callable[..., MergedConfig]
) -> None:
    config_file = merged_config(
        {"ci": {"web_identity_token_file": "/var/run/secrets/token"}}
    )

    with pytest.raises(WebIdentityConfigurationError, match="role_arn"):
        await _setup(mode, "profile", config_file=config_file, profile_name="ci")
