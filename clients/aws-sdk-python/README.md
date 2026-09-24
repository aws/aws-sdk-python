# AWS SDK for Python v4

The `aws-sdk-python` meta-package provides a convenient way to install
supported AWS service clients at compatible versions.

> **Note:** This SDK is experimental and in early development. Breaking changes
> may occur prior to the release of version 1.0.0.

## Installation

To install one client:

```bash
python -m pip install "aws-sdk-python[bedrock-runtime]"
```

To install several clients at compatible versions:

```bash
python -m pip install "aws-sdk-python[bedrock-runtime,sts]"
```

To install all supported clients:

```bash
python -m pip install "aws-sdk-python[all]"
```

## Documentation

- [API Reference](https://docs.aws.amazon.com/sdk-for-python/v4/reference/clients/) -
  the available clients, operations, and types.
- [Developer Guide](https://docs.aws.amazon.com/sdk-for-python/v4/guide/) -
  configuration, authentication, and usage of the AWS SDK for Python v4.
