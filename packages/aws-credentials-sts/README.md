# aws-credentials-sts

This package provides STS-based credential resolvers and a chain provider:

- `AssumeRoleCredentialsResolver` - assumes an explicit `role_arn` using
  credentials from a `source_resolver`.
- `ProfileAssumeRoleCredentialsResolver` - assumes a role configured in a
  named profile in the shared config/credentials files.

## Installation

```shell
uv pip install aws-credentials-sts
```

Once installed, the provider registers itself with the SDK's modular credential
chain. When a client resolves credentials through the default chain, it
will attempt to assume the role configured in the active profile
(`role_arn`/`source_profile`/`credential_source`), unless a higher-precedence
source resolves credentials first.

## Client Configuration

To use this resolver explicitly, set the `aws_credentials_identity_resolver`
property on a service client's config to an `AssumeRoleCredentialsResolver`
instance. It assumes `role_arn` using credentials from the `source_resolver`:

```python
from aws_credentials_sts.aio import AssumeRoleCredentialsResolver
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig(
        aws_credentials_identity_resolver=AssumeRoleCredentialsResolver(
            source_resolver=AsyncEnvironmentCredentialsResolver(),
            role_arn="arn:aws:iam::123456789012:role/example-role",
        ),
    )
)
```

To assume the role defined in a named profile instead, use
`ProfileAssumeRoleCredentialsResolver` with a `MergedConfig` loaded from the
shared config/credentials files:

```python
from aws_credentials_sts.aio import ProfileAssumeRoleCredentialsResolver
from smithy_aws_core.aio.config import load_config_async


async def build_client() -> ServiceClient:
    return ServiceClient(
        config=ServiceClientConfig(
            aws_credentials_identity_resolver=ProfileAssumeRoleCredentialsResolver(
                profile_name="my-profile",
                config_file=await load_config_async(),
            ),
        )
    )
```

## Standalone

Either resolver can also be used on its own to fetch credentials directly:

```python
import asyncio

from aws_credentials_sts.aio import AssumeRoleCredentialsResolver
from smithy_aws_core.aio.identity import AsyncEnvironmentCredentialsResolver


async def main() -> None:
    resolver = AssumeRoleCredentialsResolver(
        source_resolver=AsyncEnvironmentCredentialsResolver(),
        role_arn="arn:aws:iam::123456789012:role/example-role",
    )
    identity = await resolver.get_identity(properties={})


asyncio.run(main())
```
