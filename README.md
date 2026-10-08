## AWS SDK for Python v4
[![Apache 2 licensed][apache-badge]][apache-url]

[apache-badge]: https://img.shields.io/badge/license-APACHE2-blue.svg
[apache-url]: https://github.com/aws/aws-sdk-python/blob/main/LICENSE

> [!WARNING]
> The AWS SDK for Python v4 is **experimental** and in early development. It is intended for evaluation and testing in pre-production environments only. Do not use it for production workloads. APIs and behavior might change before general availability.
>
> **For production deployments, use [Boto3](https://github.com/boto/boto3)**: the established, generally available AWS SDK for Python with full coverage of all AWS services.

This repository contains the next-generation AWS SDK for Python v4, rebuilt from
the ground up with an async-first, modular architecture. These new clients allow
you to interact with select AWS services using Python's native `async`/`await`
functionality. Unlike Boto3, these clients are distributed per-service, leaving
you the option to install only what fits your needs.

### Key features

+ **Native asynchronous APIs**: Service clients use Python `async` and `await` for non-blocking operations and concurrent I/O.
+ **Bidirectional streaming**: Supported clients can send and receive event streams concurrently over HTTP/2.
+ **Modular packages**: Each service client is available as a separate package (e.g., `aws-sdk-dynamodb`), reducing the dependencies you install and deploy.
+ **Generated types**: Type annotations provide editor completion and static-analysis support.

### When to use this SDK vs. Boto3

| | **AWS SDK for Python v4** | **[Boto3](https://github.com/boto/boto3)** |
| --- | --- | --- |
| Release status | Experimental | General Availability |
| Production use | Not recommended | Yes |
| Architecture | Async-first, modular per-service packages | Synchronous, monolithic package |
| Service coverage | 24 services (expanding) | All AWS services |

**Choose [Boto3](https://github.com/boto/boto3) if you** need production stability, full AWS service coverage, synchronous workloads, or features like paginators, waiters, and presigned URLs.

**Choose the AWS SDK for Python v4 if you** are evaluating native async capabilities, building high-throughput async prototypes, working with streaming services in test environments, or want to provide feedback to shape the GA release.

## Installation

The SDK requires Python 3.12 or later and publishes each service client as a
separate package. For example, the following command installs the DynamoDB
and Transcribe Streaming clients as individual packages:

```bash
python -m pip install aws-sdk-dynamodb aws-sdk-transcribe-streaming
```

The same clients are also available as optional dependencies of the
`aws-sdk-python` meta-package:

```bash
python -m pip install "aws-sdk-python[dynamodb,transcribe_streaming]"
```

The meta-package installs only the service clients that you select as extras;
without extras, it installs no clients. It coordinates client versions through
its MAJOR.MINOR version, so it installs compatible client versions together.

Use the meta-package when your application depends on several clients. Install
individual client packages when your application uses only one or two services
and you want the smallest dependency set.

## Quick start

First, create a virtual environment to keep this project's packages separate
from other Python projects, and activate it:

```bash
python -m venv .venv
source .venv/bin/activate
```

Then install the Amazon STS client used in this example:

```bash
python -m pip install aws-sdk-sts
```

Next, set up credentials (in e.g. `~/.aws/credentials`):

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN
```

For the credential sources that the experimental SDK supports, see
[Credential providers](https://docs.aws.amazon.com/sdk-for-python/v4/guide/credential-providers.html)
in the developer guide.

Then, set up a default Region (in e.g. `~/.aws/config`):

```ini
[default]
region = us-east-1
```

Finally, run the following example, which calls Amazon STS `GetCallerIdentity`
to verify your setup:

```python
import asyncio

from aws_sdk_sts.client import AsyncSTSClient
from aws_sdk_sts.models import GetCallerIdentityInput


async def main():
    async with AsyncSTSClient() as client:
        response = await client.get_caller_identity(GetCallerIdentityInput())
        print(f"Account: {response.account}")
        print(f"Arn: {response.arn}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Bidirectional streaming transport

Some operations use bidirectional (duplex) event streams. The default aiohttp
transport doesn't support duplex streaming. To use these operations, install
the client's `awscrt` extra and set `AWSCRTHTTPClient` as the transport:

```bash
python -m pip install "aws-sdk-bedrock-runtime[awscrt]"
```

```python
from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
from smithy_http.aio.crt import AWSCRTHTTPClient


async def create_client() -> AsyncBedrockRuntimeClient:
    config = await AsyncBedrockRuntimeConfig.resolve(
        region="us-east-1",
        transport=AWSCRTHTTPClient(),
    )
    return AsyncBedrockRuntimeClient(config=config)
```

## Resources

+ [SDK Homepage](https://aws.amazon.com/sdk-for-python/)
+ [Developer Guide](https://docs.aws.amazon.com/sdk-for-python/v4/guide/welcome.html)
+ [API Reference](https://docs.aws.amazon.com/sdk-for-python/v4/reference/)

## Feedback

The SDK uses **GitHub Issues** to track feature requests and issues with the SDK.
You can provide feedback or report a bug by submitting an [issue](https://github.com/aws/aws-sdk-python/issues/new/choose).
This is the preferred mechanism to give feedback so that other users can engage in the conversation, +1 issues, etc.

## Security

See [CONTRIBUTING](https://github.com/aws/aws-sdk-python/blob/develop/CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
