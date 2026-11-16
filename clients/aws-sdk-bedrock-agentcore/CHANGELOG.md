# Changelog

## v0.13.0

### API Changes
* Adds the dimension name to evaluation results and batch evaluation summaries. For multi-dimensional LLM-as-a-Judge evaluators, each result and summary now identifies which dimension it corresponds to.
* Adds AgentCore Runtime session endpoint support, including sessionEndpointUrl on the InvokeAgentRuntime response
* Adds the Builtin.FailureAnalysis evaluator for batch evaluations. GetBatchEvaluation now returns insightResults that group session failures into insights with root causes and suggested fixes.
* Support SigV4 request signing (cryptographically signed) in the Bedrock AgentCore Harness MCP connector tool.
* AgentCore Memory now supports Long-Term Memory Time-to-Live on Batch APIs.
* Adds the InvokeWebSearch API, which searches the web using the AWS-managed web search and returns ranked results with a text extract from each page. Results can be filtered by domain and by publication time.

### Breaking Changes
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `BedrockAgentCoreClient` and `BedrockAgentCoreConfig` in `aws_sdk_bedrock_agentcore.client` and `aws_sdk_bedrock_agentcore.config`. The async `AsyncBedrockAgentCoreClient` and `AsyncBedrockAgentCoreConfig` moved to `aws_sdk_bedrock_agentcore.aio.client` and `aws_sdk_bedrock_agentcore.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_bedrock_agentcore`. Event stream operations are only available on the async client.
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.

### Features
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.

### Enhancements
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Add support for Python 3.15.
* Load models, schemas, and operations lazily on first use.

### Dependencies
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.

## v0.12.0

### API Changes
* AgentCore Memory now supports direct ingestion into long-term memory via IngestData API.
* Batch evaluation now supports up to 10 CloudWatch log groups per CloudWatchLogsSource.
* Batch evaluation now supports evaluating specific traces within a session. Each session can specify up to 100 trace IDs to evaluate.
* Adds log group name prefix trace source selection, custom or source log group result destinations, and metrics namespace customization.
* Amazon Bedrock AgentCore Harness now supports lifecycle hooks for invocations and tool calls, with Lambda, SNS, and EventBridge targets. This release also adds apiBase for custom OpenAI-compatible endpoints.

### Enhancements
* Re-generated with smithy-python 0.6.0

### Dependencies
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.11.0

### API Changes
* Increase spans count from 1k to 20k
* AgentCore Memory now supports Flexible Namespaces and Non-Conversational Payloads in CreateEvent API
* Add support for the Machine Payments Protocol (MPP) and x402 upto scheme payments protocol in Amazon Bedrock AgentCore Payments. Customers can now pay for MPP-gated resources and also pay services which requires upto scheme in x402

### Enhancements
* Re-generated with smithy-python 0.5.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.10.0` to `~=0.11.0`.
* Bump `smithy-http` from `~=0.4.0` to `~=0.5.0`.

## v0.10.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.9.0` to `~=0.10.0`.

## v0.9.0

### API Changes
* Adding online eval arn as input for recommendation API.
* Add support for capacity provider sessions in Amazon Bedrock AgentCore. Customers can now delete an active session running on a runtime instance launched through their capacity provider.

### Dependencies
* Bump `smithy-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-aws-core` from `~=0.8.0` to `~=0.9.0`.

## v0.8.0

### Features
* Initial client release with support for current Amazon Bedrock AgentCore operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.
