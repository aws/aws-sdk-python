#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures public definitions come before private ones, in modules and in classes.

A reader opening a file should meet its API first and its machinery last. With a
fixed order, the public surface of any file or class is read top-down without
scanning, and review diffs that move a symbol between public and private stand
out. Within a class, dunders (lifecycle) come first, then public members, then
private ones.

Python needs a name defined before code that runs at import time uses it, such
as a base class, a decorator, a default value, an eager annotation or a class
attribute. A private definition used that way by a later public one takes the
public one's place in the order.
"""

import ast
from pathlib import Path

from _common import Finding, analyzed_modules, main

type _Def = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def check() -> list[Finding]:
    findings: list[Finding] = []
    for module in analyzed_modules():
        lazy = _lazy_annotations(module.tree)
        findings.extend(
            _order(module.path, module.tree.body, scope="module", lazy=lazy)
        )
        for node in ast.walk(module.tree):
            if isinstance(node, ast.ClassDef):
                findings.extend(
                    _order(
                        module.path, node.body, scope=f"class {node.name}", lazy=lazy
                    )
                )
    return findings


_DEF_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _rank(name: str, *, in_class: bool) -> int:
    if in_class and name.startswith("__") and name.endswith("__"):
        return 0
    return 2 if name.startswith("_") else 1


def _order(
    path: Path, body: list[ast.stmt], *, scope: str, lazy: bool
) -> list[Finding]:
    findings: list[Finding] = []
    in_class = scope != "module"
    ranks = _effective_ranks(body, in_class=in_class, lazy=lazy)
    highest = 0
    highest_name = ""
    for node, effective in zip(body, ranks, strict=True):
        if not isinstance(node, _DEF_TYPES):
            continue
        rank = _rank(node.name, in_class=in_class)
        if rank < highest:
            kind = {0: "dunder", 1: "public"}[rank]
            findings.append(
                Finding(
                    f"{scope}: {kind} {node.name} follows {highest_name}",
                    path,
                    node.lineno,
                )
            )
        elif effective > highest:
            highest, highest_name = effective, node.name
    return findings


def _effective_ranks(body: list[ast.stmt], *, in_class: bool, lazy: bool) -> list[int]:
    """Rank each statement, lowered to that of any later statement needing it."""
    # Other statements stay where they are, so they rank as the highest
    # definition above them.
    ranks: list[int] = []
    above = 0
    for s in body:
        if isinstance(s, _DEF_TYPES):
            ranks.append(_rank(s.name, in_class=in_class))
            above = max(above, ranks[-1])
        elif not in_class and _defines_public(s):
            ranks.append(1)
        else:
            ranks.append(above)
    eager = [_eager_names(s, lazy=lazy) for s in body]
    changed = True
    while changed:
        changed = False
        for i, stmt in enumerate(body):
            if not isinstance(stmt, _DEF_TYPES):
                continue
            for j in range(i + 1, len(body)):
                if stmt.name in eager[j] and ranks[j] < ranks[i]:
                    ranks[i] = ranks[j]
                    changed = True
    return ranks


def _eager_names(stmt: ast.stmt, *, lazy: bool) -> set[str]:
    """Names a statement reads when it executes, excluding function bodies."""
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = stmt.args
        nodes: list[ast.AST | None] = [
            *stmt.decorator_list,
            *args.defaults,
            *args.kw_defaults,
        ]
        if not lazy:
            params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
            params += [a for a in (args.vararg, args.kwarg) if a is not None]
            nodes += [p.annotation for p in params] + [stmt.returns]
        return {n for node in nodes for n in _loads(node)}
    if isinstance(stmt, ast.ClassDef):
        names = {
            n
            for node in [*stmt.decorator_list, *stmt.bases, *stmt.keywords]
            for n in _loads(node)
        }
        for member in stmt.body:
            names |= _eager_names(member, lazy=lazy)
        return names
    if isinstance(stmt, ast.AnnAssign) and lazy:
        return _loads(stmt.value) | _loads(stmt.target)
    if isinstance(stmt, ast.TypeAlias):
        return set()
    return _loads(stmt)


def _defines_public(stmt: ast.stmt) -> bool:
    return any(
        isinstance(n, ast.Name)
        and isinstance(n.ctx, ast.Store)
        and not n.id.startswith("_")
        for n in ast.walk(stmt)
    )


def _loads(node: ast.AST | None) -> set[str]:
    if node is None:
        return set()
    return {
        n.id
        for n in ast.walk(node)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }


def _lazy_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(s, ast.ImportFrom)
        and s.module == "__future__"
        and any(a.name == "annotations" for a in s.names)
        for s in tree.body
    )


if __name__ == "__main__":
    main("source order", check)
