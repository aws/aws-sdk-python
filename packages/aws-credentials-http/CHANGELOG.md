# Changelog

## v0.4.0

### Bug fixes
* Skip the retry delay after the final failed attempt when fetching container credentials.

### Dependencies
* Bump `smithy-aws-core` from `~=0.11.0` to `~=0.12.0`.
* Bump `smithy-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-http` from `~=0.5.0` to `~=0.6.0`.

## v0.3.0

### Dependencies
* Bump `smithy-aws-core` from `~=0.10.0` to `~=0.11.0`.
* Bump `smithy-http` from `~=0.4.0` to `~=0.5.0`.

## v0.2.0

### Bug fixes
* Normalize empty container credential URI query strings to `None`.

### Dependencies
* Bump `smithy-aws-core` from `~=0.9.0` to `~=0.10.0`.

## v0.1.0

### Features
* Add container HTTP credentials resolver and `EcsContainer` chain provider.

### Dependencies
* Bump `smithy-aws-core` from `~=0.8.0` to `~=0.9.0`.
* Bump `smithy-core` from `~=0.7.0` to `~=0.8.0`.
