# Changelog

## v0.13.1

### Enhancements
* Update README with Developer Preview release status.

## v0.13.0

### API Changes
* Adds Retrieval Instructions for Amazon Bedrock Knowledge Bases. Create, get, update, delete, list, and version customer-authored instructions that guide how a knowledge base retrieves and answers, with content review before use.
* Add support for configuring searchability for metadata fields via UpdateKnowledgeBase request for Managed Knowledge Base. Once a field is marked as searchable it can be queried via query text and is factored into Managed Knowledge Base's ranking algorithm.

### Breaking Changes
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `BedrockAgentClient` and `BedrockAgentConfig` in `aws_sdk_bedrock_agent.client` and `aws_sdk_bedrock_agent.config`. The async `AsyncBedrockAgentClient` and `AsyncBedrockAgentConfig` moved to `aws_sdk_bedrock_agent.aio.client` and `aws_sdk_bedrock_agent.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_bedrock_agent`.

### Features
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.

### Enhancements
* Load models, schemas, and operations lazily on first use.
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Add support for Python 3.15.

### Dependencies
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.

## v0.12.0

### API Changes
* Adds support for calling VPC configuration API's in Bedrock. These configurations allow the use of On Prem connectors in Bedrock Managed Knowledge bases.
* TwelveLabs Marengo 3.0 is now an embedding model option in Amazon Bedrock Managed Knowledge Base. Create multimodal embeddings for video, audio, and image content that capture visual scenes, speech, and video cues, not just transcribed text.
* Adds an optional textReadyAt field to ListIngestionJobs and GetIngestionJob for Managed Knowledge Bases data source sync jobs. The field denotes the timestamp at which all the documents in the scope of a sync job had their text content indexed and are available for retrieval.
* Adds an optional syncSchedule field to CreateDataSource and UpdateDataSource for Managed Knowledge Bases data source connectors, so a data source can sync automatically on a daily, weekly, or monthly schedule.

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

### Features
* Initial client release with support for current Agents for Amazon Bedrock operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.
