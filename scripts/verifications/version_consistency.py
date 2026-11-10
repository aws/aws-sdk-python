#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures each package's ``__version__`` matches its distribution version.

``__version__`` is what user-agent strings, bug reports and customer feature
gates read; the distribution version is what resolvers and PyPI read. If they
disagree, telemetry and support misattribute behavior to the wrong release. The
version should also come from one place, sourced the same way in every package.
"""

import importlib
import importlib.metadata

from _common import Finding, main, packages


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
        elif package.version_file is None:
            findings.append(
                Finding(
                    f"{package.dist}: dynamic version without a hatch version path",
                    pyproject,
                )
            )
        if package.source_version is None:
            findings.append(
                Finding(
                    f"{package.dist}: __version__ is not a literal in the package source",
                    pyproject,
                    severity="warning",
                )
            )
        try:
            installed = importlib.metadata.version(package.dist)
        except importlib.metadata.PackageNotFoundError:
            findings.append(Finding(f"{package.dist}: not installed", pyproject))
            continue
        for root in package.roots:
            runtime = getattr(importlib.import_module(root), "__version__", None)
            if runtime is None:
                findings.append(
                    Finding(f"{root} defines no __version__", package.src / root)
                )
            elif runtime != installed:
                findings.append(
                    Finding(
                        f"{root}.__version__ is {runtime!r}, distribution version is {installed!r}",
                        package.src / root / "__init__.py",
                    )
                )
    return findings


if __name__ == "__main__":
    main("version consistency", check)
