# aws-credentials-sts

This package provides STS-based credential resolvers and chain providers:

- `AssumeRoleCredentialsResolver` - assumes an explicit `role_arn` using
  credentials from a `source_resolver`.
- `ProfileAssumeRoleCredentialsResolver` - assumes a role configured in a
  named profile in the shared config/credentials files.
- `WebIdentityCredentialsResolver` - assumes `role_arn` with an OIDC token read
  from `web_identity_token_file`, using STS `AssumeRoleWithWebIdentity`.

Each resolver and provider has an async equivalent in `aws_credentials_sts.aio`.

## Installation

```shell
uv pip install aws-credentials-sts
```

Once installed, the providers register themselves with the SDK's modular
credential chain. When a client resolves credentials through the default chain,
unless a higher-precedence source resolves credentials first, it will:

- assume a role with web identity when the `AWS_WEB_IDENTITY_TOKEN_FILE` and
  `AWS_ROLE_ARN` environment variables are set, and `AWS_ROLE_SESSION_NAME`
  optionally names the session. This is skipped when a profile is selected
  explicitly.
- assume the role configured in the active profile
  (`role_arn`/`source_profile`/`credential_source`).
- assume a role with web identity configured in the active profile
  (`web_identity_token_file`/`role_arn`/`role_session_name`).

## Client Configuration

To use this resolver explicitly, set the `aws_credentials_identity_resolver`
property on a service client's config to an `AssumeRoleCredentialsResolver`
instance. It assumes `role_arn` using credentials from the `source_resolver`:

```python
from aws_credentials_sts import AssumeRoleCredentialsResolver
from smithy_aws_core.identity import EnvironmentCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig.resolve(
        aws_credentials_identity_resolver=AssumeRoleCredentialsResolver(
            source_resolver=EnvironmentCredentialsResolver(),
            role_arn="arn:aws:iam::123456789012:role/example-role",
        ),
    )
)
```

To assume the role defined in a named profile instead, use
`ProfileAssumeRoleCredentialsResolver` with a `MergedConfig` loaded from the
shared config/credentials files:

```python
from aws_credentials_sts import ProfileAssumeRoleCredentialsResolver
from smithy_aws_core.config import load_config


def build_client() -> ServiceClient:
    return ServiceClient(
        config=ServiceClientConfig.resolve(
            aws_credentials_identity_resolver=ProfileAssumeRoleCredentialsResolver(
                profile_name="my-profile",
                config_file=load_config(),
            ),
        )
    )
```

To assume a role with web identity explicitly, use
`WebIdentityCredentialsResolver`. The token file is read each time the
credentials are refreshed, so a token rotated on disk is picked up:

```python
from aws_credentials_sts import WebIdentityCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig.resolve(
        aws_credentials_identity_resolver=WebIdentityCredentialsResolver(
            role_arn="arn:aws:iam::123456789012:role/example-role",
            web_identity_token_file="/var/run/secrets/token",
        ),
    )
)
```

## Standalone

Any resolver can also be used on its own to fetch credentials directly:

```python
import asyncio

from aws_credentials_sts.aio import AsyncAssumeRoleCredentialsResolver
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver


async def main() -> None:
    resolver = AsyncAssumeRoleCredentialsResolver(
        source_resolver=AsyncEnvironmentCredentialsResolver(),
        role_arn="arn:aws:iam::123456789012:role/example-role",
    )
    identity = await resolver.get_identity(properties={})


asyncio.run(main())
```
