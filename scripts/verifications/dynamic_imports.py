#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Bans ``importlib.import_module`` and ``__import__`` with non-literal arguments in shipped code.

An import whose target is computed at runtime is invisible to every static tool:
the dependency, cycle, import-direction and canonical-import verifications,
type checkers, bundlers and freezers all miss it. Requiring a string literal
keeps the import graph those tools see complete, since the shared import index
records literal calls as imports.
"""

import ast

from _common import (
    Finding,
    Module,
    analyzed_modules,
    import_call_aliases,
    is_import_call,
    main,
    module_findings,
)


def check() -> list[Finding]:
    return module_findings(_module_findings, analyzed_modules())


def _module_findings(module: Module) -> list[Finding]:
    findings: list[Finding] = []
    aliases = import_call_aliases(module.tree)
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call) or not is_import_call(node.func, aliases):
            continue
        first = node.args[0] if node.args else None
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            findings.append(
                Finding(
                    f"dynamic import with non-literal target: {ast.unparse(node)[:120]}",
                    module.path,
                    node.lineno,
                )
            )
    return findings


if __name__ == "__main__":
    main("dynamic imports", check)
