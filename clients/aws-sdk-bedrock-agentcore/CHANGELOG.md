# Changelog

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
