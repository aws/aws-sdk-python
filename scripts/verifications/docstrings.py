#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures public classes, functions, methods and constants have docstrings.

Docstrings are the API reference customers read in their editor and in the
generated docs; an undocumented public symbol is a blank page there. Internal
symbols (underscore-prefixed, dunders, or anything in an underscore-prefixed
module) are exempt, since nobody outside the package reads them. Classes,
functions and methods are checked with ruff's pydocstyle rules. A method that
overrides a documented one is exempt, since editors and the generated docs show
the inherited docstring (``inspect.getdoc``) for it. Module-level
constants carry an attribute docstring (a string literal right after the
assignment), which no ruff rule checks, so that part is an AST pass.
"""

import ast
import functools
import importlib
import inspect
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _common import (
    ROOT,
    Finding,
    Module,
    Package,
    analyzed_modules,
    main,
    model_data_globs,
    module_findings,
    packages,
    run,
    runtime_modules,
)

_SELECT = "D101,D102,D103,D106"
_CONSTANT = re.compile(r"^[A-Z][A-Z0-9_]*$")
_LOCATION = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+):\d+: (?P<message>(?P<code>D\d+) .*)"
)


def check() -> list[Finding]:
    return [
        *(f for f in _ruff_findings() if not _inherits_docstring(f)),
        *module_findings(_constant_findings, analyzed_modules()),
    ]


def _ruff_findings() -> list[Finding]:
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        return [
            f for found in pool.map(_package_ruff_findings, packages()) for f in found
        ]


def _package_ruff_findings(package: Package) -> list[Finding]:
    ruff = str(Path(sys.executable).parent / "ruff")
    proc = run(
        [
            ruff,
            "check",
            "--config",
            str(package.dir / "pyproject.toml"),
            "--select",
            _SELECT,
            "--output-format",
            "concise",
            "--no-cache",
            *(
                arg
                for glob in model_data_globs(package)
                for arg in ("--extend-exclude", glob)
            ),
            str(package.src),
        ]
    )
    return [
        Finding(match["message"], (ROOT / match["path"]).resolve(), int(match["line"]))
        for line in proc.stdout.splitlines()
        if (match := _LOCATION.match(line)) is not None
    ]


def _inherits_docstring(finding: Finding) -> bool:
    """Whether a D102 method overrides one whose docstring editors and docs show."""
    if not finding.message.startswith("D102 ") or finding.path is None:
        return False
    module = _modules_by_path().get(finding.path)
    if module is None:
        return False
    qualname = _method_qualname(module.tree, finding.line)
    if qualname is None:
        return False
    for package in packages():
        if str(package.src) not in sys.path:
            sys.path.insert(0, str(package.src))
    try:
        obj: object = importlib.import_module(module.name)
        for part in qualname:
            obj = getattr(obj, part)
    except Exception:  # noqa: BLE001
        return False
    return inspect.getdoc(obj) is not None


@functools.cache
def _modules_by_path() -> dict[Path, Module]:
    return {m.path.resolve(): m for m in runtime_modules()}


def _method_qualname(tree: ast.Module, line: int) -> list[str] | None:
    def walk(body: list[ast.stmt], prefix: list[str]) -> list[str] | None:
        for node in body:
            if isinstance(node, ast.ClassDef):
                if (found := walk(node.body, [*prefix, node.name])) is not None:
                    return found
            elif (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.lineno == line
                and prefix
            ):
                return [*prefix, node.name]
        return None

    return walk(tree.body, [])


def _constant_findings(module: Module) -> list[Finding]:
    findings: list[Finding] = []
    if not module.public:
        return findings
    body = module.tree.body
    for index, node in enumerate(body):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        elif isinstance(node, ast.AnnAssign):
            target = node.target
        else:
            continue
        if not isinstance(target, ast.Name) or not _CONSTANT.match(target.id):
            continue
        following = body[index + 1] if index + 1 < len(body) else None
        documented = (
            isinstance(following, ast.Expr)
            and isinstance(following.value, ast.Constant)
            and isinstance(following.value.value, str)
        )
        if not documented:
            findings.append(
                Finding(
                    f"public constant {target.id} has no docstring",
                    module.path,
                    node.lineno,
                )
            )
    return findings


if __name__ == "__main__":
    main("docstrings", check)
