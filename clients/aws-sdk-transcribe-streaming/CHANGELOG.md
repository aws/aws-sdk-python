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
* This release adds a new optional TranscriptFormat parameter to the Amazon Transcribe streaming API, letting customers select spoken or written form for numeric and formatted output.

### Enhancements
* Re-generated with smithy-python 0.4.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.

## v0.7.0

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
* AWS Transcribe Streaming now supports specifying a resumption window for the stream through the SessionResumeWindow parameter, allowing customers to reconnect to their streams for a longer duration beyond stream start time.

### Dependencies
* Bump `smithy-core` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-http` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-aws-core` from `~=0.4.0` to `~=0.5.0`.

## v0.4.0

### Enhancements
* Re-generated with smithy-python 0.3.0
* Update package docstrings from Sphinx style to Google style for improved readability and consistency with Python community standards. ([#48](https://github.com/aws/aws-sdk-python/pull/48))

## v0.3.0

### Breaking Changes
* Function signature for `resolve_retry_strategy` has been changed to prevent unnecessary code duplication in operation methods. This will affect all 0.3.0 clients.

### Dependencies
* **Updated**: `smithy_aws_core[eventstream, json]` from `~=0.2.0` to `~=0.3.0`.
* **Updated**: `smithy_core` from `~=0.2.0` to `~=0.3.0`.

## v0.2.0

### API Changes
* This release adds support for additional locales in AWS transcribe streaming.

### Enhancements
* Add Standard Retry Mode.

### Dependencies
* **Updated**: `smithy_aws_core[eventstream, json]` from `~=0.1.0` to `~=0.2.0`.
* **Updated**: `smithy_core` from `~=0.1.0` to `~=0.2.0`.
* **Updated**: `smithy_http[awscrt]~=0.3.0` from `~=0.2.0` to `~=0.3.0`.

## v0.1.0

### Features
* Initial client release with support for current Amazon Transcribe Streaming operations.
