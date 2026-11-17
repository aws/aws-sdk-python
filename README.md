## AWS SDK for Python v4
[![Apache 2 licensed][apache-badge]][apache-url]

[apache-badge]: https://img.shields.io/badge/license-APACHE2-blue.svg
[apache-url]: https://github.com/aws/aws-sdk-python/blob/main/LICENSE

> [!WARNING]
> The AWS SDK for Python v4 is currently in **Developer Preview**. It is intended for evaluation and testing only. Do not use it for production workloads.

The AWS SDK for Python v4 is the next major version of the AWS SDK for Python and the successor to [Boto3](https://github.com/boto/boto3).

### Key features

+ **Synchronous and asynchronous clients**: Each service package provides a synchronous client and an asynchronous client that uses `asyncio` for non-blocking operations and concurrent I/O.
+ **Modular packages**: Each service client is available as a separate package, ensuring you only install services you need.
+ **Bidirectional streaming**: Supported asynchronous clients can send and receive event streams concurrently over HTTP/2.
+ **Generated types**: Every client, operation, and request and response model ships with type annotations and API documentation, so type checkers catch invalid requests before your code runs.
+ **Keyword and dictionary inputs**: Operations accept request parameters as keyword arguments, as a dictionary, or as a typed input model.

### Documentation
- [Developer Guide](https://docs.aws.amazon.com/sdk-for-python/v4/guide/welcome.html)
- [API Reference](https://docs.aws.amazon.com/sdk-for-python/v4/reference/)

### Comparison with Boto3

| Capability | **AWS SDK for Python v4** | **Boto3** |
| --- | --- | --- |
| Release status | Developer Preview | General Availability |
| Service coverage | 37 services (growing) | All AWS services |
| Paginators, waiters, presigned URLs | Not yet available | Available |

Boto3 remains fully supported. You can install both SDKs in the same application.

See [Choosing the AWS SDK for Python](https://docs.aws.amazon.com/sdk-for-python/v4/guide/choosing-sdk.html) in
the developer guide for a more detailed comparison.

## Installation

The SDK requires Python 3.12 or later. For example, the following command
installs the Amazon S3 and Amazon Bedrock Runtime clients:

```bash
python -m pip install aws-sdk-s3 aws-sdk-bedrock-runtime
```

To install several clients at compatible versions, select them as extras of the
`aws-sdk-python` meta-package, which installs only the clients that you select:

```bash
python -m pip install "aws-sdk-python[s3,bedrock-runtime]"
```

## Quick start

First, create a virtual environment to keep this project's packages separate
from other Python projects, and activate it:

```bash
python -m venv .venv
source .venv/bin/activate
```

Then install the Amazon S3 client used in this example:

```bash
python -m pip install aws-sdk-s3
```

Next, set up credentials (in e.g. `~/.aws/credentials`):

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN
```

For the credential sources that the SDK supports, see
[Credential providers](https://docs.aws.amazon.com/sdk-for-python/v4/guide/credential-providers.html)
in the developer guide.

Then, set up a default Region (in e.g. `~/.aws/config`):

```ini
[default]
region = us-east-1
```

Finally, run the following example, which calls Amazon S3 `ListBuckets` to
verify your setup. Your identity needs the `s3:ListAllMyBuckets` permission.

```python
from aws_sdk_s3 import S3Client

with S3Client() as client:
    response = client.list_buckets()
    for bucket in response.buckets or []:
        print(bucket.name)
```

To make the same call asynchronously, use the `Async` variant of the client:

```python
import asyncio

from aws_sdk_s3 import AsyncS3Client


async def main():
    async with AsyncS3Client() as client:
        response = await client.list_buckets()
        for bucket in response.buckets or []:
            print(bucket.name)


asyncio.run(main())
```

## Constructing requests

Operations accept request parameters as keyword arguments, a dictionary, or a
typed input model. The following calls are equivalent:

```python
from aws_sdk_s3 import S3Client
from aws_sdk_s3.models import ListObjectsV2Input

with S3Client() as client:
    client.list_objects_v2(bucket="amzn-s3-demo-bucket", max_keys=10)
    client.list_objects_v2({"bucket": "amzn-s3-demo-bucket", "max_keys": 10})
    client.list_objects_v2(ListObjectsV2Input(bucket="amzn-s3-demo-bucket", max_keys=10))
```

## Bidirectional streaming transport

Event stream operations are available only on asynchronous clients. The default
aiohttp transport doesn't support bidirectional (duplex) streams. To use them,
install the client's `awscrt` extra and set `AWSCRTHTTPClient` as the transport:

```bash
python -m pip install "aws-sdk-bedrock-runtime[awscrt]"
```

```python
from aws_sdk_bedrock_runtime import AsyncBedrockRuntimeClient
from aws_sdk_bedrock_runtime import AsyncBedrockRuntimeConfig
from smithy_http.aio.crt import AWSCRTHTTPClient


async def create_client() -> AsyncBedrockRuntimeClient:
    config = await AsyncBedrockRuntimeConfig.resolve(
        region="us-east-1",
        transport=AWSCRTHTTPClient(),
    )
    return AsyncBedrockRuntimeClient(config=config)
```

## Resources

+ [AWS SDK for Python Homepage](https://aws.amazon.com/sdk-for-python/)
+ [AWS SDKs and Tools Reference Guide](https://docs.aws.amazon.com/sdkref/latest/guide/overview.html)

## Feedback

The SDK uses **GitHub Issues** to track feature requests and issues with the SDK.
You can provide feedback or report a bug by submitting an [issue](https://github.com/aws/aws-sdk-python/issues/new/choose).
This is the preferred mechanism to give feedback so that other users can engage in the conversation, +1 issues, etc.

## Security

See [CONTRIBUTING](https://github.com/aws/aws-sdk-python/blob/develop/CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
