# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# pyright: strict

"""Runs one test body against both the async and the sync client of a service."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractContextManager, AsyncExitStack
from typing import Any, Literal, Self, cast

from smithy_core.interceptors import Interceptor, RequestContext
from smithy_http.interfaces import HTTPRequest

type Mode = Literal["async", "sync"]

MODES: tuple[Mode, ...] = ("async", "sync")


async def open_client[C](
    stack: AsyncExitStack,
    mode: Mode,
    create_async: Callable[[], Awaitable[C]],
    create_sync: Callable[[], AbstractContextManager[Any]],
) -> C:
    """Open a client in ``mode`` typed as the async client, closed when ``stack`` exits."""
    if mode == "async":
        client: Any = await create_async()
    else:
        # Sync and async clients share operation names and models, so the
        # adapter stands in for the async type and pyright checks every call.
        client = AwaitableClient(create_sync())
    await stack.enter_async_context(client)
    return cast(C, client)


class AwaitableClient:
    """Exposes a sync client through its async twin's awaitable interface."""

    def __init__(self, client: AbstractContextManager[Any]) -> None:
        self._client = client

    async def __aenter__(self) -> Self:
        self._client.__enter__()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        self._client.__exit__(*exc_info)

    def __getattr__(self, name: str) -> Callable[..., Awaitable[Any]]:
        operation = getattr(self._client, name)

        async def call(*args: Any, **kwargs: Any) -> Any:
            return operation(*args, **kwargs)

        return call


class RequestRecorder(Interceptor[Any, Any, HTTPRequest, Any]):
    """Records each signed request just before it is sent."""

    def __init__(self) -> None:
        self.requests: list[HTTPRequest] = []

    def read_before_transmit(self, context: RequestContext[Any, HTTPRequest]) -> None:
        self.requests.append(context.transport_request)
