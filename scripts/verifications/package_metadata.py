#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every package's pyproject.toml and layout follow the same conventions.

Customers see each package's metadata on PyPI and in their resolver: a package
claiming a different Python floor, license, or supported versions than its
siblings is either wrong or an undeclared policy split. A package missing
``py.typed`` silently drops type information for everyone who installs it. Each
field is compared against the value most packages use, so a deliberate outlier
is a visible, reviewable exception rather than drift.
"""

import json
from collections import Counter
from typing import Any

from _common import Finding, Package, main, packages


def check() -> list[Finding]:
    findings: list[Finding] = []
    rows = {p.dist: (p, _fields(p)) for p in packages()}
    keys = sorted({k for _, fields in rows.values() for k in fields})
    for key in keys:
        values = {dist: fields.get(key) for dist, (_, fields) in rows.items()}
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
        text = text.replace(f"{group}/{package.dir.name}", f"{group}/<dir>")
        if root:
            text = text.replace(root, "<root>")
        return json.loads(text)

    return {
        "requires-python": project.get("requires-python"),
        "license": project.get("license"),
        "authors": project.get("authors"),
        "readme": project.get("readme"),
        "classifiers": sorted(
            c
            for c in project.get("classifiers", [])
            if not c.startswith(_PER_PACKAGE_CLASSIFIERS)
        ),
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
        "LICENSE": (package.dir / "LICENSE").exists(),
        "tests/unit": (package.dir / "tests" / "unit").is_dir(),
        ".changes": (package.dir / ".changes").is_dir(),
    }


# Topic and audience describe what each package is, not repo-wide policy.
_PER_PACKAGE_CLASSIFIERS = ("Topic ::", "Intended Audience ::")


if __name__ == "__main__":
    main("package metadata", check)
