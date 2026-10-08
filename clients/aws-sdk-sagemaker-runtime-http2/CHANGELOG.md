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

### Dependencies
* Bump `smithy-core` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-http` from `~=0.3.0` to `~=0.4.0`.
* Bump `smithy-aws-core` from `~=0.4.0` to `~=0.5.0`.

## v0.4.0

### Enhancements
* Update package docstrings from Sphinx style to Google style for improved readability and consistency with Python community standards. ([#48](https://github.com/aws/aws-sdk-python/pull/48))
* Re-generated with smithy-python 0.3.0

## v0.3.0

This release follows 0.1.0. There is no 0.2.0 as the initial release was intended to be inline
with the `smithy-aws-core` version used in the client.

### Breaking Changes
* Function signature for `resolve_retry_strategy` has been changed to prevent unnecessary code duplication in operation methods. This will affect all 0.3.0 clients.

### Dependencies
* **Updated**: `smithy_aws_core[eventstream, json]` from `~=0.2.0` to `~=0.3.0`.
* **Updated**: `smithy_core` from `~=0.2.0` to `~=0.3.0`.

## v0.1.0

### Features
* Initial client release with support for current Amazon SageMaker Runtime HTTP2 operations.
