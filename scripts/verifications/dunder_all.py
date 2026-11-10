#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each ``__all__`` lists the module's public definitions and its re-exports.

Python never checks ``__all__``; only star imports read it. Yet type checkers,
documentation generators and IDEs treat it as the declared public surface, so a
public name missing from it is invisible to them, and a package ``__init__`` that
re-exports a name its source module doesn't export publishes something the owner
never declared public. Unresolvable names are already caught by ruff F822.

Only modules that declare ``__all__`` are checked. A name counts as public when it
is defined in the module and has no leading underscore.
"""

import ast

from _common import (
    Finding,
    analyzed_modules,
    main,
    module_index,
    owned_roots,
    resolve_from,
)

# A module-level logger is named for logging config, not imported by customers.
_NOT_API = frozenset({"logger"})


def check() -> list[Finding]:
    findings: list[Finding] = []
    index = module_index()
    for module in analyzed_modules():
        exported = module.dunder_all
        if exported is None:
            continue
        exported_set = set(exported)
        for name in sorted(module.defined - _NOT_API):
            if not name.startswith("_") and name not in exported_set:
                findings.append(
                    Finding(f"public {name} is missing from __all__", module.path)
                )
        if not module.is_package:
            continue
        used = _used_names(module.tree)
        for name, imp in sorted(module.imported.items()):
            if name.startswith("_") or imp.top not in owned_roots() or imp.name is None:
                continue
            # An import the module itself uses is a dependency, not a re-export.
            if name not in exported_set and (
                imp.context == "type_checking" or name in used
            ):
                continue
            target, attr = resolve_from(imp)
            if attr is None:
                continue
            if name not in exported_set:
                findings.append(
                    Finding(
                        f"re-exported {name} (from {target}) is missing from __all__",
                        module.path,
                        imp.line,
                        "warning",
                    )
                )
                continue
            source = index.get(target)
            source_all = (
                source.dunder_all
                if source is not None and not source.model_data
                else None
            )
            if source_all is not None and attr not in source_all:
                findings.append(
                    Finding(
                        f"re-exports {attr} from {target}, which does not list it in __all__",
                        module.path,
                        imp.line,
                    )
                )
    return findings


def _used_names(tree: ast.Module) -> set[str]:
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            try:
                annotation = ast.parse(node.value, mode="eval")
            except SyntaxError:
                continue
            used.update(n.id for n in ast.walk(annotation) if isinstance(n, ast.Name))
    return used


if __name__ == "__main__":
    main("__all__ consistency", check)
