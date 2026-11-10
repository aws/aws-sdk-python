# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Imports one module in this fresh interpreter and prints a JSON report of what happened."""

import atexit
import importlib
import json
import logging
import os
import signal
import socket
import sys
import sysconfig
import threading
import time
import traceback
import warnings
from typing import Any

_WATCHED_SIGNALS = [s for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP) if s]


def main() -> None:
    module, roots = sys.argv[1], tuple(sys.argv[2:])
    effects: list[dict[str, Any]] = []

    stdlib = sysconfig.get_paths()["stdlib"]

    def blame() -> str | None:
        """The first non-stdlib caller, when it is our code."""
        frame = sys._getframe(2)
        while frame is not None:
            filename = frame.f_code.co_filename
            if not (filename.startswith((stdlib, "<frozen")) or filename == __file__):
                return (
                    f"{filename}:{frame.f_lineno}"
                    if filename.startswith(roots)
                    else None
                )
            frame = frame.f_back
        return None

    environ_type = type(os.environ)
    original_getitem = environ_type.__getitem__
    original_setitem = environ_type.__setitem__
    original_contains = environ_type.__contains__

    def getitem(self: Any, key: str) -> Any:
        if (where := blame()) is not None:
            effects.append({"kind": "env-read", "detail": key, "where": where})
        return original_getitem(self, key)

    def setitem(self: Any, key: str, value: str) -> None:
        if (where := blame()) is not None:
            effects.append({"kind": "env-write", "detail": key, "where": where})
        original_setitem(self, key, value)

    def contains(self: Any, key: object) -> bool:
        if (where := blame()) is not None:
            effects.append({"kind": "env-read", "detail": str(key), "where": where})
        return original_contains(self, key)

    original_atexit = atexit.register

    def register(func: Any, *args: Any, **kwargs: Any) -> Any:
        effects.append(
            {
                "kind": "atexit",
                "detail": getattr(func, "__qualname__", repr(func)),
                "where": blame(),
            }
        )
        return original_atexit(func, *args, **kwargs)

    environ_type.__getitem__ = getitem  # type: ignore[method-assign]
    environ_type.__setitem__ = setitem  # type: ignore[method-assign]
    environ_type.__contains__ = contains  # type: ignore[method-assign]
    atexit.register = register  # type: ignore[assignment]

    loggers_before = _logger_state()
    threads_before = {t.ident for t in threading.enumerate()}
    path_before = list(sys.path)
    meta_path_before = list(sys.meta_path)
    excepthook_before = sys.excepthook
    timeout_before = socket.getdefaulttimeout()
    signals_before = {s: signal.getsignal(s) for s in _WATCHED_SIGNALS}
    modules_before = set(sys.modules)

    original_filterwarnings = warnings.filterwarnings
    original_simplefilter = warnings.simplefilter
    # A dependency's own filters are its business, not an effect of our import.
    third_party_filters: list[Any] = []

    def attributed(original: Any) -> Any:
        def install(*args: Any, **kwargs: Any) -> None:
            before = list(warnings.filters)
            where = blame()
            original(*args, **kwargs)
            if where is None:
                third_party_filters.extend(
                    f for f in warnings.filters if f not in before
                )

        return install

    error: dict[str, Any] | None = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        filters_before = list(warnings.filters)
        warnings.filterwarnings = attributed(original_filterwarnings)
        warnings.simplefilter = attributed(original_simplefilter)
        start = time.perf_counter()
        try:
            importlib.import_module(module)
        except BaseException as e:
            error = _describe(e)
        elapsed = time.perf_counter() - start
        warnings.filterwarnings = original_filterwarnings
        warnings.simplefilter = original_simplefilter
        filters_after = [f for f in warnings.filters if f not in third_party_filters]

    environ_type.__getitem__ = original_getitem  # type: ignore[method-assign]
    environ_type.__setitem__ = original_setitem  # type: ignore[method-assign]
    environ_type.__contains__ = original_contains  # type: ignore[method-assign]
    atexit.register = original_atexit  # type: ignore[assignment]

    for name, state in _logger_state().items():
        if loggers_before.get(name) != state and state["handlers"]:
            effects.append(
                {
                    "kind": "logging",
                    "detail": f"{name or 'root'}: {state}",
                    "where": None,
                }
            )
    if logging.root.level != loggers_before.get("", {}).get(
        "level", logging.root.level
    ):
        effects.append(
            {"kind": "logging", "detail": "root level changed", "where": None}
        )
    for thread in threading.enumerate():
        if thread.ident not in threads_before:
            effects.append({"kind": "thread", "detail": thread.name, "where": None})
    if filters_after != filters_before:
        added = [str(f) for f in filters_after if f not in filters_before]
        effects.append(
            {"kind": "warnings-filter", "detail": "; ".join(added), "where": None}
        )
    if sys.path != path_before:
        effects.append({"kind": "sys.path", "detail": "modified", "where": None})
    if sys.meta_path != meta_path_before:
        effects.append({"kind": "sys.meta_path", "detail": "modified", "where": None})
    if sys.excepthook is not excepthook_before:
        effects.append({"kind": "excepthook", "detail": "replaced", "where": None})
    if socket.getdefaulttimeout() != timeout_before:
        effects.append({"kind": "socket-timeout", "detail": "changed", "where": None})
    for sig, handler in signals_before.items():
        if signal.getsignal(sig) != handler:
            effects.append(
                {"kind": "signal", "detail": signal.Signals(sig).name, "where": None}
            )

    report = {
        "ok": error is None,
        "error": error,
        "seconds": elapsed,
        "new_modules": len(set(sys.modules) - modules_before),
        "warnings": [
            {
                "category": w.category.__name__,
                "message": str(w.message),
                "where": f"{w.filename}:{w.lineno}",
            }
            for w in caught
        ],
        "side_effects": effects,
    }
    sys.stdout.write("\n" + json.dumps(report) + "\n")


def _logger_state() -> dict[str, dict[str, Any]]:
    state: dict[str, dict[str, Any]] = {
        "": {
            "level": logging.root.level,
            "handlers": [type(h).__name__ for h in logging.root.handlers],
        }
    }
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger):
            state[name] = {
                "level": logger.level,
                "handlers": [
                    type(h).__name__
                    for h in logger.handlers
                    if not isinstance(h, logging.NullHandler)
                ],
            }
    return state


def _describe(e: BaseException) -> dict[str, Any]:
    missing = None
    cursor: BaseException | None = e
    while cursor is not None:
        if isinstance(cursor, ModuleNotFoundError) and cursor.name:
            missing = cursor.name
            break
        cursor = cursor.__cause__ or cursor.__context__
    return {
        "type": type(e).__name__,
        "message": str(e),
        "missing": missing,
        "traceback": traceback.format_exception(e)[-3:],
    }


if __name__ == "__main__":
    main()
