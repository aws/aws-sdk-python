#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every symbol in each package's public API is fully typed.

Shipping ``py.typed`` promises customers that our public API is typed. Pyright's
strict mode on our own sources doesn't verify that promise: inferred return
types, unannotated public attributes and partially unknown types type-check
internally but show up as ``Unknown`` in a customer's editor and type checker.
``pyright --verifytypes`` measures the public surface the way a consumer sees it.

It only resolves installed (non-editable) packages, so the wheels are built and
installed into a temporary venv first.
"""

import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _common import (
    Finding,
    build_wheels,
    main,
    make_venv,
    packages,
    run,
    runtime_modules,
)

_SHOWN_PER_PACKAGE = 20


def check() -> list[Finding]:
    findings: list[Finding] = []
    pyright = str(Path(sys.executable).parent / "pyright")
    with tempfile.TemporaryDirectory(prefix="type-completeness-") as tmp:
        work = Path(tmp)
        wheels = build_wheels(work / "wheels")
        venv = work / "venv"
        make_venv(venv, *map(str, wheels))

        def one(target: tuple[Path, str]) -> list[Finding]:
            path, name = target
            proc = run(
                [pyright, "--verifytypes", name, "--ignoreexternal", "--outputjson"],
                cwd=work,
                env={
                    "VIRTUAL_ENV": str(venv),
                    "PATH": f"{venv / 'bin'}:{os.environ['PATH']}",
                },
            )
            return _report(path, name, proc.stdout, proc.stderr)

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            for result in pool.map(one, _targets()):
                findings.extend(result)
    return findings


def _targets() -> list[tuple[Path, str]]:
    """Each package root, or each public non-model-data module of a generated client.

    Verifying a whole client walks its model data, which takes tens of seconds
    for the largest clients.
    """
    targets: list[tuple[Path, str]] = []
    for package in packages():
        if package.dir.parent.name != "clients":
            targets.extend((package.src / r, r) for r in package.roots)
            continue
        mine = [m for m in runtime_modules() if m.package is package]
        data = [m.name for m in mine if m.model_data]
        # pyright verifies a package's submodules too, so skip packages holding model data.
        targets.extend(
            (m.path, m.name)
            for m in mine
            if m.public
            and not m.model_data
            and not any(d.startswith(m.name + ".") for d in data)
        )
    return targets


def _report(path: Path, root: str, stdout: str, stderr: str) -> list[Finding]:
    try:
        completeness = json.loads(stdout)["typeCompleteness"]
    except (json.JSONDecodeError, KeyError):
        return [Finding(f"{root}: pyright failed: {stderr.strip()[-300:]}", path)]
    if not completeness.get("packageRootDirectory"):
        return [Finding(f"{root}: pyright did not resolve the installed package", path)]
    if not completeness.get("pyTypedPath"):
        return [
            Finding(f"{root}: no py.typed, so type checkers treat it as untyped", path)
        ]
    counts = completeness["exportedSymbolCounts"]
    total = sum(counts.values())
    # pyright scores an empty public surface 0, but nothing exported is nothing untyped.
    score = completeness["completenessScore"] if total else 1
    if score >= 1:
        return []
    findings = [
        Finding(f"{root}: {score:.1%} of {total} exported symbols fully typed", path)
    ]
    incomplete = [
        s for s in completeness["symbols"] if s["isExported"] and not s["isTypeKnown"]
    ]
    for symbol in incomplete[:_SHOWN_PER_PACKAGE]:
        first = next(
            (
                d["message"].splitlines()[0]
                for d in symbol["diagnostics"]
                if d["severity"] == "error"
            ),
            "type not known",
        )
        findings.append(Finding(f"  {symbol['name']}: {first}", path, severity="info"))
    if len(incomplete) > _SHOWN_PER_PACKAGE:
        findings.append(
            Finding(
                f"  ... {len(incomplete) - _SHOWN_PER_PACKAGE} more",
                path,
                severity="info",
            )
        )
    return findings


if __name__ == "__main__":
    main("type completeness", check)
