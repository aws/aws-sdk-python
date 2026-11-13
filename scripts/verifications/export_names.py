#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each exported class or function is exported under its own name.

An export like ``Foo = Bar`` makes tracebacks, reprs, pickles, docs and log
lines say ``Bar`` while customers wrote ``Foo``, and leaves two names for one
object that must then both be kept stable. This is the export-side complement of
the canonical-imports verification. Both ``__name__`` and ``__qualname__`` are
compared, so an exported nested object is caught too.
"""

import importlib
import inspect
import sys
import typing

from _common import (
    Finding,
    main,
    owned_roots,
    packages,
    public_runtime_module_names,
    runtime_modules,
)


def check() -> list[Finding]:
    for package in packages():
        sys.path.insert(0, str(package.src))
    findings: list[Finding] = []
    by_name = {m.name: m for m in runtime_modules()}
    paths = {name: m.path for name, m in by_name.items()}
    roots = owned_roots()
    for modname in public_runtime_module_names():
        try:
            module = importlib.import_module(modname)
        except Exception as e:
            findings.append(
                Finding(
                    f"cannot import {modname}: {e}", paths[modname], severity="warning"
                )
            )
            continue
        names = getattr(module, "__all__", None) or [
            n for n in vars(module) if not n.startswith("_")
        ]
        stub_only = [
            n
            for n in by_name[modname].stub_names
            if not n.startswith("_") and n not in names
        ]
        for name in [*names, *stub_only]:
            obj = getattr(module, name, None)
            if not _is_named(obj) or not _owned(obj, roots):
                continue
            actual = getattr(obj, "__name__", None)
            qualname = getattr(obj, "__qualname__", actual)
            if actual != name or qualname != name:
                shown = (
                    actual if qualname == actual else f"{actual} (qualname {qualname})"
                )
                findings.append(
                    Finding(
                        f"{modname}.{name} is exported under a different name: {shown}",
                        paths[modname],
                    )
                )
    return findings


def _is_named(obj: object) -> bool:
    return (
        inspect.isclass(obj)
        or inspect.isfunction(obj)
        or isinstance(obj, typing.TypeAliasType | typing.TypeVar)
    )


def _owned(obj: object, roots: frozenset[str]) -> bool:
    module = getattr(obj, "__module__", None) or ""
    return module.split(".")[0] in roots


if __name__ == "__main__":
    main("export names", check)
