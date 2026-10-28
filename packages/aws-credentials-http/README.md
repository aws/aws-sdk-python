# aws-credentials-http

This package provides a container HTTP credential resolver and chain provider.

## Installation

```shell
uv pip install aws-credentials-http
```

Once installed, the provider registers itself with the SDK's modular credential
chain. When a client resolves credentials through the default chain, it
will attempt this source when the container credential environment variables
(`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI` or `AWS_CONTAINER_CREDENTIALS_FULL_URI`)
are set, unless a higher-precedence source resolves credentials first.

## Client Configuration

To use this resolver explicitly, set the `aws_credentials_identity_resolver`
property on a service client's config to a `ContainerCredentialsResolver`
instance:

```python
from aws_credentials_http.aio import ContainerCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig(
        aws_credentials_identity_resolver=ContainerCredentialsResolver(),
    )
)
```

## Standalone

The resolver can also be used on its own to fetch credentials directly:

```python
import asyncio

from aws_credentials_http.aio import ContainerCredentialsResolver


async def main() -> None:
    resolver = ContainerCredentialsResolver()
    identity = await resolver.get_identity(properties={})


asyncio.run(main())
```
