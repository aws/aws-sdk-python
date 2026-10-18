# Amazon Bedrock Runtime Client

The `aws-sdk-bedrock-runtime` package provides a client for making
requests to Amazon Bedrock Runtime.

> **Note:** This SDK is experimental and in early development. Breaking changes
> may occur prior to the release of version 1.0.0.

## Installation

```bash
python -m pip install aws-sdk-bedrock-runtime
```

## Documentation

- [API Reference](https://docs.aws.amazon.com/sdk-for-python/v4/reference/clients/bedrock-runtime/) -
  the Bedrock Runtime client, available operations, and types.
- [Developer Guide](https://docs.aws.amazon.com/sdk-for-python/v4/guide/) -
  configuration, authentication, and usage of the AWS SDK for Python v4.

## Request compression

Request compression reduces the bytes uploaded to an operation that advertises
gzip support. It does not reduce model input tokens. The client exposes three
configuration settings:

- `disable_request_compression`: disable automatic compression.
- `request_min_compression_size_bytes`: the automatic compression threshold,
  defaulting to 10,240 bytes.
- `request_compression_encoding`: explicitly select `"gzip"` regardless of the
  threshold, or leave it as `None` for automatic behavior.

For an operation with advertised gzip support, explicit configuration is:

```python
from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig

config = await AsyncBedrockRuntimeConfig.resolve(
    region="us-east-1",
    request_compression_encoding="gzip",
)
```

The current Bedrock Runtime service model does not advertise request compression.
Leave the explicit encoding unset for current Bedrock operations. Selecting gzip
on an unsupported operation fails before sending a request; the SDK does not
silently send an uncompressed request. Disabling compression while explicitly
selecting gzip is also invalid. Zstd is not currently supported.

The configuration cannot enable server-side compression support. Bedrock and
Mantle endpoints must accept compressed requests before applications can use it
with those endpoints.

This client covers modeled Bedrock Runtime operations. Mantle's provider-compatible
APIs use a separate client integration and need compression support there too.
