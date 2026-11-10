# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio

from smithy_core import URI
from smithy_core.aio.program import run_program_async
from smithy_core.aio.utils import read_streaming_blob_async
from smithy_http import Fields
from smithy_http.aio.interfaces import AsyncHTTPClient

from .._container import DEFAULT_RETRIES, DEFAULT_TIMEOUT, fetch_credentials


class AsyncHttpCredentialsClient:
    """Retrieves AWS credentials from an HTTP credentials endpoint."""

    def __init__(
        self,
        http_client: AsyncHTTPClient,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self._http_client = http_client
        # TODO: Also apply this value as the connect timeout once smithy_http's
        # HTTPRequestConfiguration supports it.
        self._timeout = timeout
        self._retries = retries

    async def get_credentials(self, uri: URI, fields: Fields) -> dict[str, str]:
        return await run_program_async(
            fetch_credentials(
                send=lambda request, config: self._http_client.send(
                    request, request_config=config
                ),
                read_body=read_streaming_blob_async,
                sleep=asyncio.sleep,
                uri=uri,
                fields=fields,
                timeout=self._timeout,
                retries=self._retries,
            )
        )
