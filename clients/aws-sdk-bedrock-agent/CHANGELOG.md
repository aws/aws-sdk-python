# Changelog

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
