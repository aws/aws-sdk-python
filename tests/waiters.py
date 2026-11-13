# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
# pyright: strict

"""Polling waiters for live tests, until the generated clients ship their own."""

import asyncio
import time
from collections.abc import Awaitable, Callable

DEFAULT_INTERVAL = 10.0
DEFAULT_TIMEOUT = 120.0


async def wait_until[T](
    read: Callable[[], Awaitable[T]],
    done: Callable[[T], bool] = lambda _: True,
    *,
    retry_on: tuple[type[Exception], ...] = (),
    interval: float = DEFAULT_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
) -> T:
    """Repeats ``read`` until it returns a result that ``done`` accepts.

    Only exceptions in ``retry_on`` are retried. Any other exception fails the test at once,
    so a real error is not hidden behind the timeout.
    """
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while True:
        try:
            result = await read()
        except retry_on as e:
            last_error = e
        else:
            if done(result):
                return result
            last_error = None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"condition not met within {timeout:.0f}s, last error: {last_error!r}"
            ) from last_error
        await asyncio.sleep(min(interval, remaining))


async def wait_until_gone(
    read: Callable[[], Awaitable[object]],
    *,
    gone_on: tuple[type[Exception], ...],
    interval: float = DEFAULT_INTERVAL,
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Repeats ``read`` until it raises one of ``gone_on``, meaning the resource no longer exists."""

    async def is_gone() -> bool:
        try:
            await read()
        except gone_on:
            return True
        return False

    await wait_until(is_gone, lambda gone: gone, interval=interval, timeout=timeout)
