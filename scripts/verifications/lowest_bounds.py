#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every package works on the lowest dependency versions it claims to support.

The lockfile pins recent versions, so a lower bound that is too low is never
exercised: code starts using a newer API, the bound stays put, and a customer
whose environment holds an older release gets an ``AttributeError`` at runtime.
This installs every package with ``--resolution lowest-direct`` into a temporary
venv, imports every shipped module, and type-checks the hand-written sources
against it. Generated clients are only imported: type-checking the largest one
takes a minute. Requirements with no lower bound at all are reported directly, since the lowest
resolution of an unbounded requirement is an arbitrary ancient release.
"""

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _common import (
    ROOT,
    Finding,
    Package,
    all_runtime_module_names,
    main,
    package_by_dist,
    packages,
    probe,
    run,
)
from packaging.utils import canonicalize_name

_SHOWN_PYRIGHT_ERRORS = 40


def check() -> list[Finding]:
    findings = _unbounded()
    targets: list[str] = []
    for package in packages():
        extras = ",".join(sorted(package.extras))
        targets.append(f"{package.dir}[{extras}]" if extras else str(package.dir))
    with tempfile.TemporaryDirectory(prefix="lowest-bounds-") as tmp:
        venv = Path(tmp) / "venv"
        created = run(["uv", "venv", "--quiet", "--python", "3.12", str(venv)])
        if created.returncode != 0:
            return [*findings, Finding(f"uv venv failed: {created.stderr[-500:]}")]
        python = str(venv / "bin" / "python")
        installed = run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                python,
                "--resolution",
                "lowest-direct",
                *targets,
            ]
        )
        if installed.returncode != 0:
            return [
                *findings,
                Finding(
                    f"lowest-direct install failed:\n{installed.stderr.strip()[-3000:]}"
                ),
            ]
        frozen = run(["uv", "pip", "freeze", "--python", python]).stdout
        findings.append(Finding(f"resolved:\n{frozen.strip()}", severity="info"))

        for name, report in sorted(probe(all_runtime_module_names(), python).items()):
            if not report["ok"]:
                error = report["error"]
                findings.append(
                    Finding(
                        f"{name} fails to import: {error['type']}: {error['message']}"
                    )
                )

        pyright = str(Path(sys.executable).parent / "pyright")

        def typecheck(package: Package) -> list[str]:
            checked = run(
                [
                    pyright,
                    "-p",
                    str(package.dir),
                    "--pythonpath",
                    python,
                    str(package.src),
                ],
                env={
                    "VIRTUAL_ENV": str(venv),
                    "PATH": f"{venv / 'bin'}:{os.environ['PATH']}",
                },
            )
            lines = checked.stdout.splitlines()
            return [line for line in lines if " - error: " in line]

        handwritten = [p for p in packages() if p.dir.parent.name != "clients"]
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            for result in pool.map(typecheck, handwritten):
                errors.extend(result)
        for line in errors[:_SHOWN_PYRIGHT_ERRORS]:
            findings.append(
                Finding(f"pyright: {line.strip().replace(str(ROOT) + '/', '')}")
            )
        if len(errors) > _SHOWN_PYRIGHT_ERRORS:
            findings.append(
                Finding(
                    f"pyright: ... {len(errors) - _SHOWN_PYRIGHT_ERRORS} more errors",
                    severity="info",
                )
            )
    return findings


def _unbounded() -> list[Finding]:
    siblings = package_by_dist()
    findings: list[Finding] = []
    for package in packages():
        reqs = [("dependencies", r) for r in package.dependencies] + [
            (f"extra {extra}", r) for extra, rs in package.extras.items() for r in rs
        ]
        for where, req in reqs:
            if canonicalize_name(req.name) in siblings:
                continue
            if not any(
                s.operator in (">=", ">", "~=", "==", "===") for s in req.specifier
            ):
                findings.append(
                    Finding(
                        f"{package.dist} {where}: {req} has no lower bound",
                        package.dir / "pyproject.toml",
                    )
                )
    return findings


if __name__ == "__main__":
    main("lowest bounds", check)
