#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Lints and type-checks each client and package against only its own dependencies.

Each project resolves its own venv, so a missing dependency surfaces here even
when a sibling would have supplied it in a shared venv. Projects run in
parallel, but each one's output is printed whole and in project order.

Usage: project_checks.py RUFF_VERSION PYRIGHT_VERSION PYTHON_VERSION PROJECT...
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ruff, pyright, python, *projects = sys.argv[1:]
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        futures = [pool.submit(_check, p, ruff, pyright, python) for p in projects]
        for project, future in zip(projects, futures, strict=True):
            ok, output = future.result()
            if ok:
                print(f"ok   {project}", flush=True)
            else:
                failed.append(project)
                print(f"FAIL {project}\n{output}", flush=True)
    if failed:
        print(
            f"\n{len(failed)} of {len(projects)} project(s) failed: {' '.join(failed)}"
        )
        return 1
    print(f"\n{len(projects)} project(s) passed.")
    return 0


def _check(project: str, ruff: str, pyright: str, python: str) -> tuple[bool, str]:
    dirs = [d for d in (f"{project}/src", f"{project}/tests") if (ROOT / d).is_dir()]
    pyproject = ROOT / project / "pyproject.toml"
    group = ["--group", "test"] if "\ntest = [" in pyproject.read_text() else []
    commands = [
        ["uvx", f"ruff@{ruff}", "check", "--config", str(pyproject), *dirs],
        ["uvx", f"ruff@{ruff}", "format", "--check", "--config", str(pyproject), *dirs],
        [
            "uv",
            "run",
            "--python",
            python,
            "--project",
            project,
            *group,
            "--with",
            f"pyright=={pyright}",
            "pyright",
            "-p",
            project,
            *dirs,
        ],
    ]
    output: list[str] = []
    ok = True
    # Every command runs, so one failing project reports lint and type errors together.
    for command in commands:
        proc = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False
        )
        if proc.returncode != 0:
            ok = False
            output.append(f"$ {' '.join(command)}\n{proc.stdout}{proc.stderr}")
    return ok, "".join(output)


if __name__ == "__main__":
    sys.exit(main())
