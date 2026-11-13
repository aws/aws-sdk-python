#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Detects dependency cycles between packages and import cycles between modules.

A package cycle means neither package can be released, installed or reasoned
about alone. A module import cycle makes import success depend on which module a
caller happens to import first, and surfaces as partially initialized module
errors far from the cause. Function-local imports are excluded since they run
after both modules finish initializing. Cycles that exist only through
``TYPE_CHECKING`` imports are reported as warnings: they break nothing at
runtime but still tangle the design.
"""

from _common import (
    Finding,
    main,
    module_index,
    packages,
    resolve_from,
    runtime_modules,
    tarjan,
)
from packaging.utils import canonicalize_name


def check() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_package_cycles())
    findings.extend(_module_cycles())
    return findings


def _package_cycles() -> list[Finding]:
    dists = {p.dist for p in packages()}
    declared: dict[str, set[str]] = {}
    for package in packages():
        reqs = [
            *package.dependencies,
            *(r for rs in package.extras.values() for r in rs),
        ]
        # An extra that requires the package's own other extras is not a cycle.
        declared[package.dist] = ({canonicalize_name(r.name) for r in reqs} & dists) - {
            package.dist
        }

    roots = {root: p.dist for p in packages() for root in p.roots}
    imported: dict[str, set[str]] = {p.dist: set() for p in packages()}
    for module in runtime_modules():
        assert module.package is not None  # noqa: S101
        for imp in module.imports:
            target = roots.get(imp.top)
            if imp.context == "runtime" and target and target != module.package.dist:
                imported[module.package.dist].add(target)

    findings: list[Finding] = []
    for label, graph in (("declared", declared), ("imported", imported)):
        for cycle in tarjan(graph):
            findings.append(
                Finding(f"{label} package dependency cycle: {' <-> '.join(cycle)}")
            )
    return findings


def _module_cycles() -> list[Finding]:
    index = module_index()
    runtime: dict[str, set[str]] = {}
    typing: dict[str, set[str]] = {}
    for module in runtime_modules():
        runtime.setdefault(module.name, set())
        typing.setdefault(module.name, set())
        for imp in module.imports:
            if imp.context == "deferred":
                continue
            target, _ = resolve_from(imp)
            if target not in index or target == module.name:
                continue
            typing[module.name].add(target)
            if imp.context == "runtime":
                runtime[module.name].add(target)

    findings: list[Finding] = []
    runtime_cycles = tarjan(runtime)
    for cycle in runtime_cycles:
        findings.append(
            Finding(
                f"module import cycle ({len(cycle)}): {' -> '.join(cycle)}",
                index[cycle[0]].path,
            )
        )
    covered = {frozenset(c) for c in runtime_cycles}
    for cycle in tarjan(typing):
        if frozenset(cycle) in covered:
            continue
        findings.append(
            Finding(
                f"module import cycle via TYPE_CHECKING ({len(cycle)}): {' -> '.join(cycle)}",
                index[cycle[0]].path,
                severity="warning",
            )
        )
    return findings


if __name__ == "__main__":
    main("import cycles", check)
