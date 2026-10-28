# aws-credentials-imds

This package provides an EC2 instance metadata (IMDSv2) credential resolver and
chain provider.

## Installation

```shell
uv pip install aws-credentials-imds
```

Once installed, the provider registers itself with the SDK's modular credential
chain. When a client resolves credentials through the default chain, it
will attempt to fetch credentials from the EC2 Instance Metadata Service when
running on an EC2 instance, unless a higher-precedence source resolves
credentials first.

## Client Configuration

To use this resolver explicitly, set the `aws_credentials_identity_resolver`
property on a service client's config to an `IMDSCredentialsResolver` instance:

```python
from aws_credentials_imds.aio import IMDSCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig(
        aws_credentials_identity_resolver=IMDSCredentialsResolver(),
    )
)
```

Endpoint mode, token TTL, and other options can be customized through an
`IMDSConfig`:

```python
from aws_credentials_imds.aio import IMDSConfig, IMDSCredentialsResolver

resolver = IMDSCredentialsResolver(
    config=IMDSConfig(endpoint_mode="IPv6", token_ttl=300),
)
```

## Standalone

The resolver can also be used on its own to fetch credentials directly:

```python
import asyncio

from aws_credentials_imds.aio import IMDSCredentialsResolver


async def main() -> None:
    resolver = IMDSCredentialsResolver()
    identity = await resolver.get_identity(properties={})


asyncio.run(main())
```
