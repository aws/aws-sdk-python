# Changelog

## v0.5.0

### Features
* Added `WebIdentityCredentialsResolver` and `AsyncWebIdentityCredentialsResolver`, which resolve credentials with STS `AssumeRoleWithWebIdentity` from an OIDC token file, and the `WebIdentityTokenEnvProvider` and `ProfileWebIdentityProvider` chain providers (with `Async*` equivalents), so the default credential chain uses web identity configured by the `AWS_WEB_IDENTITY_TOKEN_FILE` and `AWS_ROLE_ARN` environment variables or a profile's `web_identity_token_file` and `role_arn`.

### Bug fixes
* The AssumeRole chain provider no longer claims a profile that sets `role_arn` and `web_identity_token_file` without `source_profile` or `credential_source`, so the profile resolves through web identity instead of failing.

## v0.4.0

### Dependencies
* Bump `aws-sdk-sts` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.3.0

### Dependencies
* Bump `aws-sdk-sts` from `~=0.10.0` to `~=0.11.0`.
* Bump `smithy-aws-core` from `~=0.10.0` to `~=0.11.0`.
* Bump `smithy-http` from `~=0.4.0` to `~=0.5.0`.

## v0.2.0

### Dependencies
* Update STS credential resolution to use the new async client configuration API.
* Bump `aws-sdk-sts` from `~=0.9.0` to `~=0.10.0`.
* Bump `smithy-aws-core` from `~=0.9.0` to `~=0.10.0`.

## v0.1.0

### Features
* Add STS AssumeRole credential resolvers and `ProfileAssumeRole` chain provider.

### Dependencies
* Bump `aws-sdk-sts` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-aws-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-core` from `~=0.7.0` to `~=0.8.0`.
