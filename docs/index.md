# AWS SDK for Python v4

The AWS SDK for Python v4 provides synchronous and asynchronous clients for
supported AWS services. Each service has its own package.

!!! warning "Developer Preview"

    The AWS SDK for Python v4 is intended for evaluation and testing only. Do
    not use it for production workloads; use
    [Boto3](https://docs.aws.amazon.com/boto3/latest/)
    instead.

[Browse clients](clients/index.md){ .md-button .md-button--primary }
[View source](https://github.com/aws/aws-sdk-python){ .md-button }

## Features

- **Sync and async clients.** Each package includes a synchronous client and an
  asynchronous client that works with `asyncio`. Both clients use the same
  models.
- **Per-service packages.** Install only the clients your application uses.
- **Generated types.** Each client and its data types are generated from the
  service's Smithy model. Operations take keyword arguments and return typed
  objects instead of dictionaries.
- **Streaming support.** The asynchronous clients for streaming services
  support event streams and bidirectional streaming.

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

=== "Sync"

    ```python
    from aws_sdk_dynamodb import DynamoDBClient, DynamoDBConfig

    config = DynamoDBConfig.resolve(region="us-east-1")

    with DynamoDBClient(config=config) as client:
        response = client.list_tables(limit=10)
        for table in response.table_names or []:
            print(table)
    ```

=== "Async"

    ```python
    import asyncio

    from aws_sdk_dynamodb import AsyncDynamoDBClient, AsyncDynamoDBConfig


    async def main():
        config = await AsyncDynamoDBConfig.resolve(region="us-east-1")

        async with AsyncDynamoDBClient(config=config) as client:
            response = await client.list_tables(limit=10)
            for table in response.table_names or []:
                print(table)


    asyncio.run(main())
    ```

The config's `resolve()` method loads shared settings such as retry
configuration. Here, the `region` argument overrides a region set in the
environment or shared config. The client resolves credentials through the
default chain when it sends the request.

## Documentation and support

- [Browse client API references](clients/index.md)
- [Contribute to the SDK](contributing.md)
- [Report a bug or request a feature](https://github.com/aws/aws-sdk-python/issues/new/choose)
