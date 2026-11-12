#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each package's ``__version__`` matches its distribution version.

``__version__`` is what user-agent strings, bug reports and customer feature
gates read; the distribution version is what resolvers and PyPI read. If they
disagree, telemetry and support misattribute behavior to the wrong release. The
version should also come from one place, sourced the same way in every package.

Everything is read from the source tree, because installed metadata lags the
source whenever an editable install isn't rebuilt after a version bump.
"""

import ast
from pathlib import Path

from _common import Finding, Package, main, packages


def check() -> list[Finding]:
    findings: list[Finding] = []
    for package in packages():
        pyproject = package.dir / "pyproject.toml"
        project = package.pyproject["project"]
        dynamic = "version" in project.get("dynamic", [])
        if not dynamic:
            findings.append(
                Finding(
                    f"{package.dist}: static version {project.get('version')!r} in pyproject.toml; "
                    "other packages read it from __version__",
                    pyproject,
                )
            )
            findings.extend(_check_static(package, str(project.get("version"))))
        else:
            findings.extend(_check_dynamic(package))
    return findings


def _check_dynamic(package: Package) -> list[Finding]:
    """Hatch reads the version file, so every root must agree with its literal."""
    pyproject = package.dir / "pyproject.toml"
    version_file = package.version_file
    if version_file is None:
        return [
            Finding(
                f"{package.dist}: dynamic version without a hatch version path",
                pyproject,
            )
        ]
    if not version_file.exists():
        return [
            Finding(f"{package.dist}: hatch version path does not exist", pyproject)
        ]
    expected = _literal_version(version_file)
    if expected is None:
        return [
            Finding(
                f"{package.dist}: hatch version path has no literal __version__",
                version_file,
            )
        ]
    findings: list[Finding] = []
    for root in package.roots:
        init = package.src / root / "__init__.py"
        found = _literal_version(init)
        if found is None:
            findings.append(Finding(f"{root} defines no literal __version__", init))
        elif found != expected:
            findings.append(
                Finding(
                    f"{root}.__version__ is {found!r}, distribution version is {expected!r}",
                    init,
                )
            )
    return findings


def _check_static(package: Package, expected: str) -> list[Finding]:
    """A static version is a second source, so every root must still agree with it."""
    findings: list[Finding] = []
    for root in package.roots:
        init = package.src / root / "__init__.py"
        found = _literal_version(init)
        if found is None:
            findings.append(Finding(f"{root} defines no literal __version__", init))
        elif found != expected:
            findings.append(
                Finding(
                    f"{root}.__version__ is {found!r}, static version is {expected!r}",
                    init,
                )
            )
    return findings


def _version_value(path: Path) -> ast.expr | None:
    if not path.exists():
        return None
    for node in ast.parse(path.read_text()).body:
        match node:
            case ast.Assign(targets=targets, value=value) if any(
                isinstance(t, ast.Name) and t.id == "__version__" for t in targets
            ):
                return value
            # Generated clients annotate it: ``__version__: str = "..."``.
            case ast.AnnAssign(target=ast.Name(id="__version__"), value=value):
                return value
            case _:
                pass
    return None


def _literal_version(path: Path) -> str | None:
    value = _version_value(path)
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


if __name__ == "__main__":
    main("version consistency", check)
