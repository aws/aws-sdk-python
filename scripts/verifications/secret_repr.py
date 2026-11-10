#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures objects holding secrets never render them in ``repr`` or ``str``.

Credentials, tokens and keys end up in reprs through logging, tracebacks, debugger
output and error messages, where they are copied into log stores and tickets.
Dataclasses render every field by default, so a new secret field leaks unless
someone remembers to opt it out. Each of our classes with a secret-named
constructor parameter is built with sentinel values, and its ``repr`` and ``str``
must not contain any of them.
"""

import importlib
import inspect
import re
import sys
from typing import Any

from _common import Finding, main, members, packages, runtime_modules

_SECRET = re.compile(
    r"(^|_)(secret\w*|\w*token|password|passphrase|api_key|private_key)$", re.IGNORECASE
)


def check() -> list[Finding]:
    for package in packages():
        sys.path.insert(0, str(package.src))
    findings: list[Finding] = []
    seen: set[type] = set()
    for module in runtime_modules():
        try:
            loaded = importlib.import_module(module.name)
        except Exception:  # noqa: S112
            continue
        for name, cls in members(module, loaded):
            if not inspect.isclass(cls) or cls.__module__ != module.name or cls in seen:
                continue
            seen.add(cls)
            if inspect.isabstract(cls) or getattr(cls, "_is_protocol", False):
                continue
            findings.extend(_check_class(module.path, name, cls))
    return findings


def _check_class(path: Any, name: str, cls: type) -> list[Finding]:
    try:
        params = inspect.signature(cls).parameters
    except (TypeError, ValueError):
        return []
    secrets = {p: f"SENTINEL-{p}-{id(cls)}" for p in params if _SECRET.search(p)}
    if not secrets:
        return []
    kwargs: dict[str, Any] = {}
    for param in params.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.name in secrets:
            kwargs[param.name] = secrets[param.name]
        elif param.default is param.empty:
            kwargs[param.name] = _placeholder(param)
    try:
        instance = cls(**kwargs)
    except Exception as e:
        return [
            Finding(
                f"{name}: could not construct to inspect {sorted(secrets)}: {type(e).__name__}: {e}",
                path,
                severity="warning",
            )
        ]
    findings: list[Finding] = []
    for render in (repr, str):
        try:
            text = render(instance)
        except Exception:  # noqa: S112
            continue
        leaked = sorted(p for p, sentinel in secrets.items() if sentinel in text)
        if leaked:
            findings.append(
                Finding(f"{name}: {render.__name__}() shows {', '.join(leaked)}", path)
            )
    return findings


def _placeholder(param: inspect.Parameter) -> Any:
    annotation = str(param.annotation)
    if "str" in annotation:
        return "placeholder"
    if "int" in annotation:
        return 0
    return None


if __name__ == "__main__":
    main("secret repr", check)
