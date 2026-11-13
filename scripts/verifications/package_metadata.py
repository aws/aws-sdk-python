#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every package's pyproject.toml and layout follow the same conventions.

Customers see each package's metadata on PyPI and in their resolver: a package
claiming a different Python floor, license, or supported versions than its
siblings is either wrong or an undeclared policy split. A package missing
``py.typed`` silently drops type information for everyone who installs it.

Classifiers must equal ``_CLASSIFIERS`` and every package must ship the repo's
LICENSE, since both are repo-wide policy. Every other field is compared against
the value most packages of the same kind use, so a deliberate outlier is a
visible, reviewable exception rather than drift. Generated clients and
hand-written packages are compared separately, since codegen sets the clients'
conventions and outnumbers the packages. Packages at 0.0.0 are placeholders, so
the changelog files and unit tests they can't have yet are not compared.

``--fix`` rewrites hand-written packages' classifiers and copies the LICENSE
into every package missing one. Generated clients' classifiers come from
codegen, so they are left to it.
"""

import json
import re
import shutil
import sys
from collections import Counter
from typing import Any

from _common import METAPACKAGE, ROOT, Finding, Package, is_generated, main, packages
from packaging.version import Version

_CLASSIFIERS = (
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: Apache Software License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Programming Language :: Python :: 3.15",
    "Programming Language :: Python :: Free Threading :: 2 - Beta",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Software Development :: Libraries",
)


def check() -> list[Finding]:
    findings: list[Finding] = []
    for package in packages():
        findings.extend(_check_policy(package))
    for generated in (True, False):
        group = [p for p in packages() if is_generated(p.dir) == generated]
        findings.extend(_compare(group))
    return findings


def fix() -> None:
    """Repair classifiers of hand-written packages and copy missing LICENSE files."""
    for package in packages():
        if not (package.dir / "LICENSE").exists():
            shutil.copyfile(ROOT / "LICENSE", package.dir / "LICENSE")
        if is_generated(package.dir):
            continue
        pyproject = package.dir / "pyproject.toml"
        text = pyproject.read_text()
        match = _CLASSIFIERS_BLOCK.search(text)
        if match is None:
            continue
        indent = match["indent"] or "  "
        items = "".join(f'{indent}"{c}",\n' for c in _CLASSIFIERS)
        pyproject.write_text(
            text[: match.start()] + f"classifiers = [\n{items}]" + text[match.end() :]
        )


def _check_policy(package: Package) -> list[Finding]:
    findings: list[Finding] = []
    pyproject = package.dir / "pyproject.toml"
    actual = set(package.pyproject["project"].get("classifiers", []))
    missing = sorted(set(_CLASSIFIERS) - actual)
    extra = sorted(actual - set(_CLASSIFIERS))
    if missing:
        findings.append(
            Finding(f"{package.dist}: missing classifiers {missing}", pyproject)
        )
    if extra:
        findings.append(
            Finding(f"{package.dist}: non-canonical classifiers {extra}", pyproject)
        )
    if not (package.dir / "LICENSE").exists():
        findings.append(Finding(f"{package.dist}: no LICENSE file", pyproject))
    return findings


def _compare(group: list[Package]) -> list[Finding]:
    findings: list[Finding] = []
    rows = {p.dist: (p, _fields(p)) for p in group}
    keys = sorted({k for _, fields in rows.values() for k in fields})
    for key in keys:
        values = {
            dist: fields[key] for dist, (_, fields) in rows.items() if key in fields
        }
        counts = Counter(json.dumps(v, sort_keys=True) for v in values.values())
        majority, _ = counts.most_common(1)[0]
        for dist, value in sorted(values.items()):
            encoded = json.dumps(value, sort_keys=True)
            if encoded != majority:
                package = rows[dist][0]
                findings.append(
                    Finding(
                        f"{dist}: {key} = {encoded} (most packages: {majority})",
                        package.dir / "pyproject.toml",
                    )
                )
    return findings


def _fields(package: Package) -> dict[str, Any]:
    project = package.pyproject["project"]
    tool = package.pyproject.get("tool", {})
    build = package.pyproject.get("build-system", {})
    roots = package.roots
    root = roots[0] if roots else ""

    def templated(value: Any) -> Any:
        text = json.dumps(value)
        # Scoped to the path so the aws-sdk-python package doesn't match the repo name.
        group = package.dir.parent.name
        text = text.replace(f"{group}/{package.dir.name}", "<group>/<dir>")
        if root:
            text = text.replace(root, "<root>")
        return json.loads(text)

    unreleased = package.current_version == Version("0.0.0")
    fields: dict[str, Any] = {
        "requires-python": project.get("requires-python"),
        "license": project.get("license"),
        "authors": project.get("authors"),
        "readme": project.get("readme"),
        "urls": templated(project.get("urls")),
        "version source": "dynamic"
        if "version" in project.get("dynamic", [])
        else "static",
        "hatch version path": templated(
            tool.get("hatch", {}).get("version", {}).get("path")
        ),
        "build backend": build.get("build-backend"),
        "build requires": build.get("requires"),
        "hatch build exclude": tool.get("hatch", {}).get("build", {}).get("exclude"),
        "ruff src": tool.get("ruff", {}).get("src"),
        "single import root": len(roots) == 1,
        "py.typed": all((package.src / r / "py.typed").exists() for r in roots),
        "README.md": (package.dir / "README.md").exists(),
        "CHANGELOG.md": (package.dir / "CHANGELOG.md").exists(),
        "NOTICE": (package.dir / "NOTICE").exists(),
        "tests/unit": (package.dir / "tests" / "unit").is_dir(),
        ".changes": (package.dir / ".changes").is_dir(),
    }
    # Release tooling creates the changelog files, and a placeholder has no code to test.
    if unreleased:
        for key in _RELEASE_FIELDS:
            del fields[key]
    # The metapackage has no code; meta-package-check covers it.
    if package.dir == METAPACKAGE:
        fields.pop("tests/unit", None)
    return fields


_RELEASE_FIELDS = ("CHANGELOG.md", ".changes", "tests/unit")

_CLASSIFIERS_BLOCK = re.compile(
    r"^classifiers = \[\n(?P<indent>[ \t]*)[^\]]*\]", re.MULTILINE
)


if __name__ == "__main__":
    if "--fix" in sys.argv[1:]:
        fix()
        packages.cache_clear()
    main("package metadata", check)
