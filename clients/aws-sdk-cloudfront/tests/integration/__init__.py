# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Live CloudFront integration tests, written once and run in both sync and async modes."""

import uuid

from aws_sdk_cloudfront.aio.client import AsyncCloudFrontClient
from aws_sdk_cloudfront.aio.config import AsyncCloudFrontConfig
from aws_sdk_cloudfront.client import CloudFrontClient
from aws_sdk_cloudfront.config import CloudFrontConfig
from aws_sdk_cloudfront.models import (
    CachePolicyConfig,
    CachePolicyCookieBehavior,
    CachePolicyCookiesConfig,
    CachePolicyHeaderBehavior,
    CachePolicyHeadersConfig,
    CachePolicyQueryStringBehavior,
    CachePolicyQueryStringsConfig,
    ParametersInCacheKeyAndForwardedToOrigin,
)

REGION = "us-west-2"

# Lets an interrupted run's leftovers be found and removed.
NAME_PREFIX = "aws-sdk-python-integ-"


def unique_name() -> str:
    return f"{NAME_PREFIX}{uuid.uuid4().hex[:16]}"


def cache_policy_config(name: str, *, default_ttl: int = 60) -> CachePolicyConfig:
    """A cache policy that keys on nothing, which is the cheapest valid shape."""
    return CachePolicyConfig(
        name=name,
        comment="aws-sdk-python integration test",
        min_ttl=0,
        default_ttl=default_ttl,
        max_ttl=3600,
        parameters_in_cache_key_and_forwarded_to_origin=ParametersInCacheKeyAndForwardedToOrigin(
            enable_accept_encoding_gzip=False,
            headers_config=CachePolicyHeadersConfig(
                header_behavior=CachePolicyHeaderBehavior.NONE
            ),
            cookies_config=CachePolicyCookiesConfig(
                cookie_behavior=CachePolicyCookieBehavior.NONE
            ),
            query_strings_config=CachePolicyQueryStringsConfig(
                query_string_behavior=CachePolicyQueryStringBehavior.NONE
            ),
        ),
    )


async def create_async_client() -> AsyncCloudFrontClient:
    config = await AsyncCloudFrontConfig.resolve(region=REGION)
    return AsyncCloudFrontClient(config=config)


def create_sync_client() -> CloudFrontClient:
    config = CloudFrontConfig.resolve(region=REGION)
    return CloudFrontClient(config=config)
