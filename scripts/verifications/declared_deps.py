#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each package declares every distribution it imports, and imports every one it declares.

An import of a library the importing package never declared still works whenever
something else installed it: a transitive dependency, or a sibling in a shared
venv. Tests only reach the modules they exercise, so it can pass CI and then
fail for a customer who installs that package alone.
Conversely, a declared dependency nothing imports forces an unneeded install and
resolution constraint on every customer. Typing-only imports count as uses: type
checkers in a customer's environment need the dependency installed too.
"""

from _common import (
    METAPACKAGE,
    Finding,
    import_to_dists,
    is_stdlib,
    main,
    packages,
    runtime_modules,
)
from packaging.utils import canonicalize_name


def check() -> list[Finding]:
    findings: list[Finding] = []
    mapping = import_to_dists()
    by_package: dict[str, list] = {}
    for module in runtime_modules():
        assert module.package is not None  # noqa: S101
        by_package.setdefault(module.package.dist, []).extend(module.imports)

    for package in packages():
        own = set(package.roots)
        required = {canonicalize_name(r.name) for r in package.dependencies}
        optional = {
            canonicalize_name(r.name) for reqs in package.extras.values() for r in reqs
        }
        declared = required | optional
        used: set[str] = set()
        reported: set[tuple[str, str]] = set()
        for imp in by_package.get(package.dist, []):
            top = imp.top
            if not top or top in own or is_stdlib(top):
                continue
            # Type checkers resolve typing_extensions from typeshed's bundled stdlib stubs.
            if top == "typing_extensions" and imp.context == "type_checking":
                continue
            dists = mapping.get(top)
            if not dists:
                key = (top, "unresolved")
                if key not in reported:
                    reported.add(key)
                    findings.append(
                        Finding(
                            f"{package.dist}: import {top} maps to no installed distribution",
                            imp.module.path,
                            imp.line,
                            crash=imp.context != "type_checking" and not imp.guarded,
                        )
                    )
                continue
            used.update(dists)
            if not dists & declared:
                key = (top, "undeclared")
                if key not in reported:
                    reported.add(key)
                    findings.append(
                        Finding(
                            f"{package.dist}: imports {top} ({', '.join(sorted(dists))}) "
                            f"without declaring it ({imp.context})",
                            imp.module.path,
                            imp.line,
                            crash=imp.context != "type_checking" and not imp.guarded,
                        )
                    )
        # The metapackage exists to install clients through its extras, not to import them.
        if package.dir == METAPACKAGE:
            continue
        for dist in sorted(declared - used):
            where = "dependencies" if dist in required else "optional-dependencies"
            findings.append(
                Finding(
                    f"{package.dist}: declares {dist} in {where} but never imports it",
                    package.dir / "pyproject.toml",
                )
            )
    return findings


if __name__ == "__main__":
    main("declared dependencies", check)
