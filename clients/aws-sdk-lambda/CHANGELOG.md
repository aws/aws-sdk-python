# Changelog

## v0.13.1

### Enhancements
* Update README with Developer Preview release status.

## v0.13.0

### API Changes
* Adds ConsumptionMode to SelfManagedKafkaEventSourceConfig, letting Lambda event source mappings consume self-managed Apache Kafka topics as a queue. Set ConsumptionMode to Queue when creating an event source mapping.
* Adds support for customer-managed runtimes in the CreateFunction and UpdateFunctionConfiguration APIs. Functions can now use a customer-managed runtime and receive its updates automatically, or pin to a specific runtime version using the existing runtime controls.
* AWS Lambda now supports OAuth 2.0 (OAUTHBEARER), IAM, and IAM with OAUTHBEARER authentication for self-managed Apache Kafka event source mappings, including optional OAuth scope, audience, logical cluster, and identity pool parameters. OAuth 2.0 is also available for Confluent Schema Registry.
* AWS Lambda durable functions now supports payloads up to 1 MB for checkpoints, callback completion, and error details.
* Doc updates to reposition Lambda Functions as Lambda Event Functions
* AWS Lambda now supports an optional X-Ray trace header for chained invocations in durable executions, enabling child invocations to be linked to the initiating span.

### Breaking Changes
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `LambdaClient` and `LambdaConfig` in `aws_sdk_lambda.client` and `aws_sdk_lambda.config`. The async `AsyncLambdaClient` and `AsyncLambdaConfig` moved to `aws_sdk_lambda.aio.client` and `aws_sdk_lambda.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_lambda`. Event stream operations are only available on the async client.
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.

### Features
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.

### Enhancements
* Add support for Python 3.15.
* Load models, schemas, and operations lazily on first use.
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.

### Dependencies
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.

## v0.12.0

### API Changes
* Updates documentation for lambda function timeout.
* AWS Lambda now provides configurable control over S3 direct access, allowing you to explicitly enable or disable how functions stream file reads directly from S3 buckets. This gives you flexibility to tune data access behavior based on your workload requirements, independent of memory size.

### Enhancements
* Re-generated with smithy-python 0.6.0

### Dependencies
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.11.0

### API Changes
* Adds support for full JSON resource-based policies, enabling customers to create, retrieve, update, and delete function resource policies as complete JSON documents.

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

### Features
* Initial client release with support for current AWS Lambda operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.
