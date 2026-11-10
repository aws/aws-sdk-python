#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every dependency specifier in the repo agrees, and in-repo ones track sibling versions.

Each client and package resolves on its own, so diverging specifiers for the same
dependency go unnoticed in any one of them, but a customer installing a subset of
our packages gets whatever range happens to apply, and two packages may be
uninstallable together. Dev groups and build requirements diverging from each
other means different parts of the repo are tested against different
assumptions. In-repo dependencies of shipped packages must also be bounded and
satisfied by the sibling's current version, or a release can float onto a
sibling version that lacks the code it needs.
"""

import tomllib
from collections.abc import Iterator
from pathlib import Path

from _common import ROOT, Finding, main, package_by_dist, packages, run
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name


def check() -> list[Finding]:
    findings = _in_repo_bounds()
    specs: dict[str, dict[str, list[str]]] = {}
    for pyproject, where, req in _declarations():
        specs.setdefault(canonicalize_name(req.name), {}).setdefault(
            str(req.specifier) or "(any)", []
        ).append(f"{pyproject.parent.relative_to(ROOT).as_posix() or '.'} {where}")
    for name, variants in sorted(specs.items()):
        if len(variants) > 1:
            listed = "; ".join(
                f"{s} ({', '.join(users)})" for s, users in sorted(variants.items())
            )
            findings.append(Finding(f"{name} has {len(variants)} specifiers: {listed}"))
    return findings


def _in_repo_bounds() -> list[Finding]:
    findings: list[Finding] = []
    siblings = package_by_dist()
    for package in packages():
        reqs = [("dependencies", r) for r in package.dependencies] + [
            (f"extra {extra}", r) for extra, rs in package.extras.items() for r in rs
        ]
        for where, req in reqs:
            name = canonicalize_name(req.name)
            sibling = siblings.get(name)
            if sibling is None or name == package.dist:
                continue
            version = sibling.current_version
            pyproject = package.dir / "pyproject.toml"
            if not req.specifier:
                findings.append(
                    Finding(
                        f"{package.dist} {where}: in-repo {name} is unbounded",
                        pyproject,
                    )
                )
            elif version is not None and not SpecifierSet(str(req.specifier)).contains(
                version, prereleases=True
            ):
                findings.append(
                    Finding(
                        f"{package.dist} {where}: in-repo {name}{req.specifier} excludes "
                        f"its current version {version}",
                        pyproject,
                    )
                )
    return findings


def _declarations() -> Iterator[tuple[Path, str, Requirement]]:
    """Every requirement in every tracked pyproject.toml, with where it is declared."""
    tracked = run(["git", "ls-files", "*pyproject.toml"]).stdout.split()
    for rel in tracked:
        pyproject = ROOT / rel
        data = tomllib.loads(pyproject.read_text())
        project = data.get("project", {})
        own = canonicalize_name(project.get("name", ""))
        sources = [("build-system", data.get("build-system", {}).get("requires", []))]
        sources.append(("dependencies", project.get("dependencies", [])))
        sources += [
            (f"extra {name}", reqs)
            for name, reqs in project.get("optional-dependencies", {}).items()
        ]
        sources += [
            (f"group {name}", reqs)
            for name, reqs in data.get("dependency-groups", {}).items()
        ]
        for where, reqs in sources:
            for req in reqs:
                # Group entries may be {include-group = ...} tables, not requirements.
                if not isinstance(req, str):
                    continue
                requirement = Requirement(req)
                # An extra that requires the package's own other extras is not a dependency.
                if canonicalize_name(requirement.name) != own:
                    yield pyproject, where, requirement


if __name__ == "__main__":
    main("dependency specifiers", check)
