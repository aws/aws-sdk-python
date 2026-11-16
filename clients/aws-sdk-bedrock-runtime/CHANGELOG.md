# Changelog

## v0.13.0

### Breaking Changes
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `BedrockRuntimeClient` and `BedrockRuntimeConfig` in `aws_sdk_bedrock_runtime.client` and `aws_sdk_bedrock_runtime.config`. The async `AsyncBedrockRuntimeClient` and `AsyncBedrockRuntimeConfig` moved to `aws_sdk_bedrock_runtime.aio.client` and `aws_sdk_bedrock_runtime.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_bedrock_runtime`. Event stream operations are only available on the async client.

### Features
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.

### Enhancements
* Add support for Python 3.15.
* Load models, schemas, and operations lazily on first use.
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.

### Dependencies
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.

## v0.12.0

### Enhancements
* Re-generated with smithy-python 0.6.0

### Dependencies
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.11.0

### Enhancements
* Re-generated with smithy-python 0.5.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.10.0` to `~=0.11.0`.
* Bump `smithy-http` from `~=0.4.0` to `~=0.5.0`.

## v0.10.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.9.0` to `~=0.10.0`.

## v0.9.0

### Dependencies
* Bump `smithy-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-aws-core` from `~=0.8.0` to `~=0.9.0`.

## v0.8.0

### API Changes
* Added support for mid-conversation tool changes in the Amazon Bedrock Converse and ConverseStream APIs.

### Enhancements
* Re-generated with smithy-python 0.4.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.

## v0.7.0

### API Changes
* Support system role in message.
* Support Request Metadata for Invoke Model and Invoke Model with Response Stream.
* InvokeGuardrailChecks API evaluates prompts and responses against safety checks (content filters, prompt attacks, sensitive info) without creating guardrail resources. It's a detect-only API, returning numeric scores so you can build adaptive logic as per your application.

### Enhancements
* Re-generated with smithy-python 0.3.1

### Dependencies
* Bump `smithy-core` from `~=0.5.0` to `~=0.6.0`.
* Bump `smithy-aws-core` from `~=0.6.0` to `~=0.7.0`.

## v0.6.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.5.0` to `~=0.6.0`.
* Bump `smithy-core` from `~=0.4.0` to `~=0.5.0`.

## v0.5.0

### API Changes
* Relax ToolUseId pattern to allow dots and colons

### Dependencies
* Bump `smithy-core` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-http` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-aws-core` from `~=0.4.0` to `~=0.5.0`.

## v0.4.0

### API Changes
* Added support for extended prompt caching with one hour TTL.
* Added support for structured outputs to Converse and ConverseStream APIs.

### Enhancements
* Re-generated with smithy-python 0.3.0
* Update package docstrings from Sphinx style to Google style for improved readability and consistency with Python community standards. ([#48](https://github.com/aws/aws-sdk-python/pull/48))

## v0.3.0

### API Changes
* Adds support for Audio Blocks and Streaming Image Output plus new Stop Reasons of malformed_model_output and malformed_tool_use.
* Adds support for Bedrock Runtime Reserved Service.

### Breaking Changes
* Function signature for `resolve_retry_strategy` has been changed to prevent unnecessary code duplication in operation methods. This will affect all 0.3.0 clients.

### Enhancements
* Add comprehensive integration tests for non-streaming, output streaming, and bidirectional streaming operations.

### Dependencies
* **Updated**: `smithy_aws_core[eventstream, json]` from `~=0.2.0` to `~=0.3.0`.
* **Updated**: `smithy_core` from `~=0.2.0` to `~=0.3.0`.

## v0.2.0

### API Changes
* Add support to automatically enforce safeguards across accounts within an AWS Organization.
* This release includes support for Search Results.
* Amazon Bedrock Runtime Service Tier Support Launch.
* Add support for system tool and web citation response.

### Enhancements
* Add Standard Retry Mode.

### Dependencies
* **Updated**: `smithy_aws_core[eventstream, json]` from `~=0.1.0` to `~=0.2.0`.
* **Updated**: `smithy_core` from `~=0.1.0` to `~=0.2.0`.
* **Updated**: `smithy_http[awscrt]~=0.3.0` from `~=0.2.0` to `~=0.3.0`.

## v0.1.1

### API Changes
* New stop reason for Converse and ConverseStream.

### Breaking Changes
* Removed unused `serialize.py` and `deserialize.py` modules.

### Enhancements
* Improvements to the underlying AWS CRT HTTP client result in a significant decrease in CPU usage. Addresses [aws-sdk-python#11](https://github.com/aws/aws-sdk-python/issues/11).

### Dependencies
* **Updated**: `smithy_http[awscrt]` from `~=0.1.0` to `~=0.2.0`.

## v0.1.0

### API Changes
* Fixed stop sequence limit for converse API.
* Launch CountTokens API to allow token counting.
* This release adds support for Automated Reasoning checks output models for the Amazon Bedrock Guardrails ApplyGuardrail API.
* Document update to support on-demand custom model.
* Add API Key and document citations support for Bedrock Runtime APIs.
* This release adds native h2 support for the Bedrock Runtime API. Support is limited to SDKs that support h2 requests natively.
* You can now reference images and documents stored in Amazon S3 when using InvokeModel and Converse APIs with Amazon Nova Lite and Nova Pro. This enables direct integration of S3-stored multimedia assets in your model requests without manual downloading or base64 encoding.

### Dependencies
* Updated support for all smithy dependencies in the 0.1.x minor version.

## v0.0.2

### Dependencies
* Updated support for all smithy dependencies in the 0.0.x minor version.

## v0.0.1

### Features
* Initial Client Release with support for current Amazon Bedrock Runtime operations.
* Added support for new InvokeModelWithBidirectionalStream API.
