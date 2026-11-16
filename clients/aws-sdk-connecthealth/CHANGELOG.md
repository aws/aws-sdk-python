# Changelog

## v0.13.0

### Breaking Changes
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `ConnectHealthClient` and `ConnectHealthConfig` in `aws_sdk_connecthealth.client` and `aws_sdk_connecthealth.config`. The async `AsyncConnectHealthClient` and `AsyncConnectHealthConfig` moved to `aws_sdk_connecthealth.aio.client` and `aws_sdk_connecthealth.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_connecthealth`. Event stream operations are only available on the async client.

### Features
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. The default endpoint changes to the `api.aws` domain, such as `health-agent.us-east-1.api.aws`. Add the `use_fips_endpoint` configuration option to select FIPS endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` environment variable and the `use_fips_endpoint` profile key.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.

### Enhancements
* Add support for Python 3.15.
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Load models, schemas, and operations lazily on first use.

### Bug fixes
* Apply endpoint trait host prefixes, such as `runtime.` and `streaming.`, to the operations that model them. Set the new `disable_host_prefix_injection` configuration option to `True` to send requests without the prefix.

### Dependencies
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.

## v0.12.0

### API Changes
* Multi language support with code switching, custom template sectionHeader now allows underscores.

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
* Expand input validation to support Unicode characters and markdown table syntax.

### Enhancements
* Re-generated with smithy-python 0.4.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.

## v0.7.0

### API Changes
* Add support for MedicalScribeBinaryAudioEvent in the Medical Scribe streaming input. This new event type lets you send audio as a raw binary payload instead of a base64-encoded value

### Enhancements
* Re-generated with smithy-python 0.3.1

### Dependencies
* Bump `smithy-core` from `~=0.5.0` to `~=0.6.0`.
* Bump `smithy-aws-core` from `~=0.6.0` to `~=0.7.0`.

## v0.6.0

### Features
* Initial client release with support for current Connect Health operations.
