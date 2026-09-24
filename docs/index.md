# AWS SDK for Python v4

The AWS SDK for Python v4 provides asynchronous clients for supported AWS services.
Each service has its own package.

!!! warning "Experimental: Not for production use"

    Use this SDK for evaluation and pre-production testing. Interfaces and
    behavior may change before general availability. Use
    [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
    for production workloads.

[Browse clients](clients/index.md){ .md-button .md-button--primary }
[View source](https://github.com/aws/aws-sdk-python){ .md-button }

## Features

- **Async operations.** Every service operation is an `async` method that works
  with `asyncio`.
- **Per-service packages.** Install only the clients your application uses.
- **Type annotations.** Operations, input models, and response models include
  type annotations, so editors and type checkers do not need separate stub
  packages.
- **Streaming support.** Clients for streaming services support event streams
  and bidirectional streaming.

The code generator builds each client from its service's
[Smithy](https://smithy.io/) model.

## Install a client

The clients require Python 3.12 or later. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

=== "One client"

    Install the Amazon DynamoDB client from its service package:

    ```bash
    python -m pip install aws-sdk-dynamodb
    ```

=== "Several clients"

    Use the `aws-sdk-python` meta-package to install several clients at
    compatible versions. Select clients with package extras:

    ```bash
    python -m pip install "aws-sdk-python[bedrock-runtime,sts]"
    ```

See [available clients](clients/index.md) for a list of service packages.

## List DynamoDB tables

Before running the example, grant an identity `dynamodb:ListTables` permission
and configure AWS credentials. The default credential chain checks these
built-in sources:

- Environment variables such as `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, and `AWS_SESSION_TOKEN`
- Shared AWS config and credentials files, including `credential_process`

Other supported providers come from `aws-credentials-*` packages. Install and
configure the package for your environment:

- `aws-credentials-sts` for profile-based AssumeRole
- `aws-credentials-http` for Amazon ECS or Amazon EKS container credentials
- `aws-credentials-imds` for Amazon EC2 instance metadata

The SDK detects installed provider packages and adds them to the chain
automatically. You do not need to pass a credential resolver or change the
client code. The IAM Identity Center (SSO) credential provider and the login
credentials provider are not yet supported.

Use the [Amazon DynamoDB client](clients/dynamodb/index.md) to list up to ten
tables in `us-east-1`:

```python
import asyncio

from aws_sdk_dynamodb.client import AsyncDynamoDBClient
from aws_sdk_dynamodb.config import AsyncDynamoDBConfig
from aws_sdk_dynamodb.models import ListTablesInput


async def main():
    config = await AsyncDynamoDBConfig.resolve(region="us-east-1")

    async with AsyncDynamoDBClient(config=config) as client:
        response = await client.list_tables(input=ListTablesInput(limit=10))
        for table in response.table_names or []:
            print(table)


asyncio.run(main())
```

`AsyncDynamoDBConfig.resolve()` loads shared settings such as retry
configuration. Here, the `region` argument overrides a region set in the
environment or shared config. The client resolves credentials through the
default chain when it sends the request.

## Documentation and support

- [Browse client API references](clients/index.md)
- [Contribute to the SDK](contributing.md)
- [Report a bug or request a feature](https://github.com/aws/aws-sdk-python/issues/new/choose)
