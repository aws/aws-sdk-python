#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each built wheel ships exactly the package's source, plus ``py.typed``.

Tests and CI import from the source tree, never from the wheel, so a module left
out by a build-config change, a missing ``py.typed``, or a test file swept into
the wheel all pass CI and reach customers. This builds the wheels and inspects
them. It also flags private modules that nothing imports: in a wheel those are
dead weight that can't be reached without reaching into private paths.
"""

import tempfile
import zipfile
from pathlib import Path

from _common import (
    Finding,
    Package,
    build_wheels,
    main,
    packages,
    resolve_from,
    runtime_modules,
)

_ALLOWED_SUFFIXES = (".py", ".pyi", ".so", ".pyd")


def check() -> list[Finding]:
    findings: list[Finding] = []
    with tempfile.TemporaryDirectory(prefix="wheel-contents-") as tmp:
        wheels = build_wheels(Path(tmp))
        by_dist = {w.name.split("-")[0].replace("_", "-").lower(): w for w in wheels}
        for package in packages():
            wheel = by_dist.get(package.dist)
            if wheel is None:
                findings.append(Finding(f"{package.dist}: no wheel built", package.dir))
                continue
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
            findings.extend(_inspect(package, wheel.name, names))
    findings.extend(_unreferenced_private_modules())
    return findings


def _inspect(package: Package, wheel: str, names: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    expected = {
        str(p.relative_to(package.src))
        for root in package.roots
        for p in (package.src / root).rglob("*.py*")
        if p.suffix in (".py", ".pyi") and "__pycache__" not in p.parts
    }
    for missing in sorted(expected - names):
        findings.append(Finding(f"{wheel}: missing {missing}", package.src / missing))
    for root in package.roots:
        if f"{root}/py.typed" not in names:
            findings.append(
                Finding(f"{wheel}: missing {root}/py.typed", package.src / root)
            )
    for name in sorted(names):
        if ".dist-info/" in name or name.endswith("/"):
            continue
        parts = name.split("/")
        if (
            "tests" in parts
            or parts[-1] == "conftest.py"
            or parts[-1].startswith("test_")
        ):
            findings.append(Finding(f"{wheel}: ships test file {name}", package.dir))
        elif parts[-1] != "py.typed" and not parts[-1].endswith(_ALLOWED_SUFFIXES):
            findings.append(
                Finding(
                    f"{wheel}: ships unexpected file {name}",
                    package.dir,
                    severity="warning",
                )
            )
        elif parts[0] not in package.roots:
            findings.append(
                Finding(
                    f"{wheel}: ships file outside its import roots: {name}", package.dir
                )
            )
    return findings


def _unreferenced_private_modules() -> list[Finding]:
    referenced: set[str] = set()
    for module in runtime_modules():
        for imp in module.imports:
            target, _ = resolve_from(imp)
            parts = target.split(".")
            referenced.update(".".join(parts[: i + 1]) for i in range(len(parts)))
    # Model data imports aren't indexed, so the packages holding it count as used.
    referenced.update(m.name for m in runtime_modules() if m.model_data)
    findings: list[Finding] = []
    for module in runtime_modules():
        leaf = module.name.split(".")[-1]
        if (
            module.public
            or module.model_data
            or module.name in referenced
            or (leaf.startswith("__") and leaf.endswith("__"))
        ):
            continue
        if any(other.startswith(module.name + ".") for other in referenced):
            continue
        findings.append(
            Finding(f"private module {module.name} is never imported", module.path)
        )
    return findings


if __name__ == "__main__":
    main("wheel contents", check)
