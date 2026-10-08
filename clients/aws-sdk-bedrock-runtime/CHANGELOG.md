# Changelog

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
