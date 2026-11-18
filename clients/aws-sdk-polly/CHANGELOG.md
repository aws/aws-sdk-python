# Changelog

## v0.13.1

### Enhancements
* Update README with Developer Preview release status.

## v0.13.0

### API Changes
* Added support for the new voices - Kenneth (en-US), Nate (en-US), Tina (de-DE), Carlos (es-US), Carolina (pt-BR), Leo (pt-BR), Curtis (en-AU), Kiara (en-IN), Arjun (en-IN) and Hyunduk (ko-KR). They are available as a Generative voices only.
* Amazon Polly now supports tagging lexicons. Use the new TagResource, UntagResource and ListTagsForResource APIs, or add tags when creating a lexicon with PutLexicon, to organize lexicons and control access with tag-based (ABAC) IAM policies.

### Breaking Changes
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `PollyClient` and `PollyConfig` in `aws_sdk_polly.client` and `aws_sdk_polly.config`. The async `AsyncPollyClient` and `AsyncPollyConfig` moved to `aws_sdk_polly.aio.client` and `aws_sdk_polly.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_polly`. Event stream operations are only available on the async client.
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.

### Features
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.

### Enhancements
* Add support for Python 3.15.
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Load models, schemas, and operations lazily on first use.

### Dependencies
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
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

### Features
* Initial client release with support for current Amazon Polly operations.
