# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
import asyncio
import ipaddress
import json

from smithy_core import URI
from smithy_core.exceptions import SmithyIdentityError
from smithy_http import Field, Fields
from smithy_http.aio import HTTPRequest
from smithy_http.aio.interfaces import HTTPClient, HTTPResponse
from smithy_http.interfaces import HTTPRequestConfiguration

_CONTAINER_METADATA_IP = "169.254.170.2"
_CONTAINER_METADATA_ALLOWED_HOSTS = {
    _CONTAINER_METADATA_IP,
    "169.254.170.23",
    "fd00:ec2::23",
    "localhost",
}
_DEFAULT_TIMEOUT = 2
_DEFAULT_RETRIES = 3
_SLEEP_SECONDS = 1


class HttpCredentialsClient:
    """Retrieves AWS credentials from an HTTP credentials endpoint."""

    def __init__(
        self,
        http_client: HTTPClient,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
        retries: int = _DEFAULT_RETRIES,
    ):
        self._http_client = http_client
        # TODO: Also apply this value as the connect timeout once smithy_http's
        # HTTPRequestConfiguration supports it.
        self._timeout = timeout
        self._retries = retries

    async def get_credentials(self, uri: URI, fields: Fields) -> dict[str, str]:
        self._validate_allowed_url(uri)
        fields.set_field(Field(name="Accept", values=["application/json"]))

        attempts = 0
        last_exc = None
        while attempts < self._retries:
            try:
                request = HTTPRequest(
                    method="GET",
                    destination=uri,
                    fields=fields,
                )
                response: HTTPResponse = await self._http_client.send(
                    request,
                    request_config=HTTPRequestConfiguration(read_timeout=self._timeout),
                )
                body = await response.consume_body_async()
                if response.status != 200:
                    raise SmithyIdentityError(
                        f"Container metadata service returned {response.status}: "
                        f"{body.decode('utf-8')}"
                    )
                try:
                    return json.loads(body.decode("utf-8"))
                except Exception as error:
                    raise SmithyIdentityError(
                        "Unable to parse JSON from container metadata: "
                        f"{body.decode('utf-8')}"
                    ) from error
            except Exception as error:
                last_exc = error
                attempts += 1
                if attempts < self._retries:
                    await asyncio.sleep(_SLEEP_SECONDS)

        raise SmithyIdentityError(
            f"Failed to retrieve container metadata after {self._retries} attempt(s)"
        ) from last_exc

    def _validate_allowed_url(self, uri: URI) -> None:
        if uri.scheme == "https":
            return

        if self._is_loopback(uri.host):
            return

        if not self._is_allowed_container_metadata_host(uri.host):
            raise SmithyIdentityError(
                f"Unsupported host '{uri.host}'. "
                f"Can only retrieve metadata from an HTTPS endpoint, a loopback "
                f"address, or one of: {', '.join(_CONTAINER_METADATA_ALLOWED_HOSTS)}"
            )

    def _is_loopback(self, hostname: str) -> bool:
        try:
            return ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _is_allowed_container_metadata_host(self, hostname: str) -> bool:
        return hostname in _CONTAINER_METADATA_ALLOWED_HOSTS
