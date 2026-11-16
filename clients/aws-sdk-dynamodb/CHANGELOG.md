# Changelog

## v0.13.0

### API Changes
* Enable account endpoint generation for existing CN and GovCloud regions
* Adds support for disassociating a replica from an Amazon DynamoDB multi-Region eventual consistency global table, so you can keep it as a single-Region table with its existing data. Also adds disassociation protection, on by default, to help prevent accidental disassociation.
* Adds StartBulkPutItems, DescribeBulkOperation, ListBulkOperations, and CancelBulkOperation for asynchronously loading Amazon S3 datasets into existing DynamoDB tables.

### Breaking Changes
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `DynamoDBClient` and `DynamoDBConfig` in `aws_sdk_dynamodb.client` and `aws_sdk_dynamodb.config`. The async `AsyncDynamoDBClient` and `AsyncDynamoDBConfig` moved to `aws_sdk_dynamodb.aio.client` and `aws_sdk_dynamodb.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_dynamodb`.
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.

### Features
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Route requests to account-based endpoints, such as `123456789012.ddb.us-west-2.amazonaws.com`, when the credentials carry an account ID. The new `account_id_endpoint_mode` configuration option, also read from the `AWS_ACCOUNT_ID_ENDPOINT_MODE` environment variable and the `account_id_endpoint_mode` profile key, accepts `preferred` (the default), `required`, or `disabled`; set it to `disabled` to keep using `dynamodb.<region>.amazonaws.com`.

### Enhancements
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Apply DynamoDB's retry defaults in the `adaptive` retry mode as well as the `standard` retry mode.
* Add support for Python 3.15.
* Load models, schemas, and operations lazily on first use.

### Dependencies
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.

## v0.12.0

### API Changes
* Adds support for filtering exported table data using FilterExpression, ProjectionExpression and KeyConditionExpression with ExportTableToPointInTime.

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

### Features
* Initial client release with support for current Amazon DynamoDB operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.9.0` to `~=0.10.0`.
