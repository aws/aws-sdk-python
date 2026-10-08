# Changelog

## v0.12.0

### API Changes
* Amazon Bedrock Agentic Retrieve now supports the Bedrock Mantle (OpenAI Responses) endpoint via a new MantleFoundationModel configuration with an optional projectId.

### Enhancements
* Re-generated with smithy-python 0.6.0

### Dependencies
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.11.0

### API Changes
* AgenticRetrieveStream API now supports Amazon Bedrock AgentCore Memory. Use the new memoryConfiguration parameter to continue a session from short-term memory and retrieve from long-term memory.
* Adds CheckIngestedDocumentAcl and GetIngestedDocumentAcl APIs to Amazon Bedrock Knowledge Bases. Customers can verify user access to documents based on ingested ACLs and retrieve full ACL details including allow and deny entries, enabling validation of ACL ingestion without test retrievals.

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
* Initial client release with support for current Agents for Amazon Bedrock Runtime operations.

### Dependencies
* Bump `smithy-aws-core` from `~=0.7.0` to `~=0.8.0`.
* Bump `smithy-core` from `~=0.6.0` to `~=0.7.0`.
