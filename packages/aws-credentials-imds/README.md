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
from aws_credentials_imds import IMDSCredentialsResolver

service_client = ServiceClient(
    config=ServiceClientConfig(
        aws_credentials_identity_resolver=IMDSCredentialsResolver(),
    )
)
```

Endpoint mode, token TTL, retries, timeout, and other options can be customized
through an `IMDSConfig`:

```python
from aws_credentials_imds import IMDSConfig, IMDSCredentialsResolver

resolver = IMDSCredentialsResolver(
    config=IMDSConfig(endpoint_mode="IPv6", token_ttl=300, max_attempts=2, timeout=2.0),
)
```

Each metadata read makes up to 4 attempts, with waits of 0.25, 0.5 and 1 seconds
between them, and each request times out after 1 second. To change the backoff
as well, pass a `retry_strategy`, which overrides `max_attempts`. The default
chain reads these settings from the environment or the shared config file:

| Setting | Environment variable | Config file key |
| --- | --- | --- |
| `max_attempts` | `AWS_METADATA_SERVICE_NUM_ATTEMPTS` | `metadata_service_num_attempts` |
| `timeout` | `AWS_METADATA_SERVICE_TIMEOUT` | `metadata_service_timeout` |

## Standalone

The resolver can also be used on its own to fetch credentials directly:

```python
import asyncio

from aws_credentials_imds.aio import AsyncIMDSCredentialsResolver


async def main() -> None:
    resolver = AsyncIMDSCredentialsResolver()
    identity = await resolver.get_identity(properties={})


asyncio.run(main())
```
