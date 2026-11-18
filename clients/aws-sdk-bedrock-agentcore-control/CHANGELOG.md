# Changelog

## v0.13.1

### Enhancements
* Update README with Developer Preview release status.

## v0.13.0

### API Changes
* Adds private certificate authority (CA) support for AgentCore Identity custom OAuth2.0 credential providers and custom JWT authorizers, enabling connections to IdPs with private CAs. Support SigV4 request signing (cryptographically signed) in the Bedrock AgentCore Harness MCP connector tool.
* Adds support for OAuth2 Authorization Server Metadata (RFC 8414) discovery URLs in custom JWT authorizer and OAuth2 credential provider configurations.
* Adds model-based routing and fallback to AgentCore Gateway rules. Rules can match the requested model, route to a specific model, and fall back across inference targets with an optional circuit breaker. Adds multi-dimensional rating scales for AgentCore Evaluations LLM-as-a-Judge evaluators.
* AgentCore Memory now supports configuring Long-Term Memory Time-to-Live (TTL) on Memory Strategies.
* Amazon Bedrock AgentCore Gateway now supports domainOverride so JWT-authorized gateways can advertise your public domain in OAuth discovery behind a proxy or custom domain. AgentCore Runtime adds warmup lifecycle hooks and specifying runtime memory via hooksConfiguration and resourceConfigurations.
* This release supports scoping Amazon Bedrock AgentCore Gateway rate limits by request header or request body field.
* Adds the ResetTokenVaultKeyMaterial API, which restores a token vault whose customer managed key was deleted by moving it to an AWS owned key. The reset permanently deletes the stored OAuth 2.0 tokens, users must consent again. Adds on-behalf-of token exchange client authentication override option.
* Adds Session Endpoint Feature on AgentCore Runtime

### Breaking Changes
* Codegen sync for [smithy-python b8ecead...d185e3b](https://github.com/smithy-lang/smithy-python/compare/b8eceadb0573bd0c757def9a2b26fe7bf938b239...d185e3b5b5ef2e24661a6256be721101631bdcb2): Add the synchronous `BedrockAgentCoreControlClient` and `BedrockAgentCoreControlConfig` in `aws_sdk_bedrock_agentcore_control.client` and `aws_sdk_bedrock_agentcore_control.config`. The async `AsyncBedrockAgentCoreControlClient` and `AsyncBedrockAgentCoreControlConfig` moved to `aws_sdk_bedrock_agentcore_control.aio.client` and `aws_sdk_bedrock_agentcore_control.aio.config`; update async imports to the `aio` paths. All four are also exported from `aws_sdk_bedrock_agentcore_control`.
* Operations take the members of their input as keyword arguments, or the whole request as a single positional-only input model or dictionary; the two can't be mixed in one call. `plugins` is keyword-only. Calls that pass the request as `input=` or pass `plugins` positionally must be updated. A request that leaves a required member unset, at any depth, raises a `TypeError` before it is sent.

### Features
* Nested structures and unions in a request may be written as dictionaries. A dictionary may contain models, but the members of a model must be models. Each structure and union reachable from an operation input has a dictionary form with a `Dict` suffix, declared in `models.pyi`.
* Generate an operation's idempotency token when it is omitted or `None`. It is generated once per call, so every retry sends the same token, and a token passed by the caller is sent unchanged.
* Support the `adaptive` retry mode, set with `retry_mode="adaptive"`, the `AWS_RETRY_MODE` environment variable, or the `retry_mode` profile key. Previously `retry_mode="adaptive"` was rejected, and the environment variable and profile key fell back to `standard` with a warning.
* Resolve endpoints from the service's endpoint rules instead of the standard regional endpoint pattern. Add the `use_fips_endpoint` and `use_dualstack_endpoint` configuration options to select FIPS and dual-stack endpoints, also read from the `AWS_USE_FIPS_ENDPOINT` and `AWS_USE_DUALSTACK_ENDPOINT` environment variables and the `use_fips_endpoint` and `use_dualstack_endpoint` profile keys.

### Enhancements
* Include a `py.typed` marker so type checkers use the types of the installed client, and expose the typed model surface, including member documentation, through `models.pyi`.
* Add support for Python 3.15.
* Load models, schemas, and operations lazily on first use.

### Dependencies
* Bump `smithy-aws-core` from `~=0.12.0` to `~=0.16.0`.
* Bump `smithy-http` from `~=0.6.0` to `~=0.10.0`.
* Bump `smithy-core` from `~=0.9.0` to `~=0.13.0`.

## v0.12.0

### API Changes
* Amazon Bedrock AgentCore Harness now supports lifecycle hooks for invocations and tool calls, with Lambda, SNS, and EventBridge targets. This release also adds apiBase for custom OpenAI-compatible endpoints.
* This release adds support for private certificate authorities on Amazon Bedrock AgentCore Gateway targets. The new certificateConfigurations parameter on CreateGatewayTarget and UpdateGatewayTarget references a PEM-encoded CA certificate in Amazon S3 or AWS Secrets Manager.
* Adds support for a new DELETE FAILED status for Bedrock AgentCore Runtimes and Bedrock AgentCore Runtime Endpoints.
* Amazon Bedrock AgentCore Gateway now supports returning the complete MCP tools list in a single response by disabling pagination for the tools list operation. This feature is available in limited preview.
* Online evaluation configurations now support up to 25 evaluators. CloudWatch Logs data sources for online evaluation now support up to 10 log groups.
* Amazon Bedrock AgentCore Runtime now supports specifying the platform version of an agent runtime through the new platformVersion field on CreateAgentRuntime, UpdateAgentRuntime, and GetAgentRuntime.
* Amazon Bedrock AgentCore Payments now supports credential rotation for payment connectors, letting you rotate API and wallet secrets for Quick Create payment auths from the console. This release also adds Type and Creation type columns to the payment managers views.
* AgentCore Identity adds Consent Portal APIs to manage portals that let end users grant OAuth authorization for agents to access resources. AgentCore Evaluation adds trace source selection by log group prefix, custom or source log group result destinations, and metrics namespace customization.

### Enhancements
* Re-generated with smithy-python 0.6.0

### Dependencies
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.11.0

### API Changes
* Adds implementations of third-party evaluators, both managed-as-a-service and as templates within custom evaluators.
* Update Dataset schema to THIRDPARTYEVALUATIONV1
* AgentCore Memory now supports Flexible Namespaces
* Adds AgentCore Payments support for CMK, Marketplace Subscriptions and QuickCreate

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
* Add support for Gateway rate limits and Runtime instances in Amazon Bedrock AgentCore. Customers can now configure rate limits scoped to control request rates, token consumption rates, and active connection rates. Customers can now create capacity providers to launch runtimes on their EC2 instances.
* Adding support for fine-grained access control for AgentCore Memory through managed AgentCore Gateway HTTP Connectors.

### Dependencies
* Bump `smithy-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-aws-core` from `~=0.8.0` to `~=0.9.0`.

## v0.8.0

### Features
* Initial client release with support for current Amazon Bedrock AgentCore Control operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.
