# Changelog

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
