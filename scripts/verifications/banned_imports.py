#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Bans test-only modules from shipped package code.

Test frameworks and helpers are dev dependencies: customers don't have them.
An import of one in shipped code works in our venv and fails on install, or worse,
pulls a test framework into a production process. Enforced with ruff's
flake8-tidy-imports banned-api rule (TID251) so the ban can later move into
pyproject.toml unchanged.
"""

import sys
from pathlib import Path

from _common import Finding, main, packages, run

_BANNED = {
    "pytest": "test framework; not a runtime dependency",
    "_pytest": "test framework; not a runtime dependency",
    "freezegun": "test dependency",
    "unittest.mock": "test-only; use a real object or a protocol",
    "smithy_test": "test helpers package; not a runtime dependency",
}


def check() -> list[Finding]:
    findings: list[Finding] = []
    ruff = str(Path(sys.executable).parent / "ruff")
    for package in packages():
        overrides: list[str] = []
        for name, msg in _BANNED.items():
            overrides += [
                "--config",
                f'lint.flake8-tidy-imports.banned-api."{name}".msg = "{msg}"',
            ]
        proc = run(
            [
                ruff,
                "check",
                "--config",
                str(package.dir / "pyproject.toml"),
                *overrides,
                "--select",
                "TID251",
                "--output-format",
                "concise",
                "--no-cache",
                str(package.src),
            ]
        )
        for line in proc.stdout.splitlines():
            if ": TID251" in line:
                findings.append(Finding(line))
        if proc.returncode not in (0, 1):
            findings.append(
                Finding(f"ruff failed for {package.dist}: {proc.stderr.strip()[-300:]}")
            )
    return findings


if __name__ == "__main__":
    main("banned imports", check)
