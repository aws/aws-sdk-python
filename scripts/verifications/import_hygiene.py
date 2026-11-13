#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every shipped module imports alone in a fresh interpreter, without optional deps at top level.

The test suite imports modules in whatever order the tests happen to, so a module
that only imports after a sibling has warmed ``sys.modules`` passes CI and fails
for the customer who imports it first. An unguarded top-level import of an
optional dependency turns a missing extra into an ``ImportError`` for anyone who
imports a module that pulls it in. A module nothing else imports is the extra's
own integration point: only a customer who chose that extra imports it, and
optional-deps checks that it fails clearly without the extra.
"""

from _common import (
    Finding,
    import_to_dists,
    main,
    module_index,
    probe,
    resolve_from,
    runtime_modules,
)
from packaging.utils import canonicalize_name


def check() -> list[Finding]:
    findings: list[Finding] = []
    modules = runtime_modules()
    reports = probe(m.name for m in modules)
    mapping = import_to_dists()
    imported = _imported_by_others()
    for module in modules:
        report = reports[module.name]
        if not report["ok"]:
            error = report["error"]
            findings.append(
                Finding(
                    f"{module.name} fails to import alone: {error['type']}: {error['message']}",
                    module.path,
                    crash=True,
                )
            )
        if module.name not in imported:
            continue
        assert module.package is not None  # noqa: S101
        optional = module.package.extras_only
        for imp in module.imports:
            if imp.context != "runtime" or imp.guarded:
                continue
            dists = {canonicalize_name(d) for d in mapping.get(imp.top, set())}
            if dists & optional:
                findings.append(
                    Finding(
                        f"unguarded top-level import of optional dependency {imp.top}",
                        module.path,
                        imp.line,
                        crash=True,
                    )
                )
    return findings


def _imported_by_others() -> set[str]:
    """Modules some other shipped module imports unguarded at runtime."""
    index = module_index()
    targets: set[str] = set()
    for module in runtime_modules():
        for imp in module.imports:
            if imp.context != "runtime" or imp.guarded:
                continue
            target, _ = resolve_from(imp)
            if target in index and target != module.name:
                targets.add(target)
    return targets


if __name__ == "__main__":
    main("import hygiene", check)
