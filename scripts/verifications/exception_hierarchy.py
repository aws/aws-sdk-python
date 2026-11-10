#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures our exceptions share a root and shipped code doesn't raise generic ones.

Customers handle runtime failures (service, transport, config, credentials) by
exception type, and need one ``except`` clause that catches every error the SDK
raises on purpose. That only works if every exception class we define derives
from the package's base error. ``Exception``, ``BaseException`` and
``RuntimeError`` give a caller nothing specific to catch, so raising them is
banned. Other builtins stay allowed: ``ValueError`` or ``TypeError`` for a bad
argument signals a bug in the caller, which nobody should catch, and protocol
methods must raise ``AttributeError``, ``KeyError`` and the like.

Test helpers (``testing`` modules) are exempt from the base-class rule, since
customers never handle their errors. Raise sites are checked statically, so a
generic exception raised and caught internally is still reported.
"""

import ast
import importlib
import inspect
import sys

from _common import (
    Finding,
    analyzed_modules,
    main,
    members,
    packages,
    runtime_modules,
)

_BASE = "smithy_core.exceptions.SmithyError"
_GENERIC = frozenset({"Exception", "BaseException", "RuntimeError"})


def check() -> list[Finding]:
    for package in packages():
        sys.path.insert(0, str(package.src))
    return [*_class_findings(), *_raise_findings()]


def _class_findings() -> list[Finding]:
    findings: list[Finding] = []
    base = _resolve(_BASE)
    for module in runtime_modules():
        if "testing" in module.name.split("."):
            continue
        try:
            loaded = importlib.import_module(module.name)
        except Exception as e:
            findings.append(
                Finding(
                    f"cannot import {module.name}: {e}", module.path, severity="warning"
                )
            )
            continue
        for name, obj in members(module, loaded):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseException)
                and not issubclass(obj, Warning)
                and obj.__module__ == module.name
                and not issubclass(obj, base)
            ):
                findings.append(
                    Finding(
                        f"{name} does not derive from {base.__qualname__}", module.path
                    )
                )
    return findings


def _raise_findings() -> list[Finding]:
    findings: list[Finding] = []
    for module in analyzed_modules():
        shadowed = set(module.defined) | set(module.imported)
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.Raise) or node.exc is None:
                continue
            exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if (
                isinstance(exc, ast.Name)
                and exc.id in _GENERIC
                and exc.id not in shadowed
            ):
                findings.append(
                    Finding(f"raises generic {exc.id}", module.path, node.lineno)
                )
    return findings


def _resolve(dotted: str) -> type:
    module, _, name = dotted.rpartition(".")
    return getattr(importlib.import_module(module), name)


if __name__ == "__main__":
    main("exception hierarchy", check)
