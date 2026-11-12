# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import time

from smithy_core import URI
from smithy_core.program import run_program
from smithy_core.utils import read_streaming_blob
from smithy_http import Fields
from smithy_http.interfaces import HTTPClient

from ._container import DEFAULT_RETRIES, DEFAULT_TIMEOUT, fetch_credentials


class HttpCredentialsClient:
    """Retrieves AWS credentials from an HTTP credentials endpoint."""

    def __init__(
        self,
        http_client: HTTPClient,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self._http_client = http_client
        # TODO: Also apply this value as the connect timeout once smithy_http's
        # HTTPRequestConfiguration supports it.
        self._timeout = timeout
        self._retries = retries

    def get_credentials(self, uri: URI, fields: Fields) -> dict[str, str]:
        """Fetch the credentials document from the endpoint at ``uri``."""
        return run_program(
            fetch_credentials(
                send=lambda request, config: self._http_client.send(
                    request, request_config=config
                ),
                read_body=read_streaming_blob,
                sleep=time.sleep,
                uri=uri,
                fields=fields,
                timeout=self._timeout,
                retries=self._retries,
            )
        )
