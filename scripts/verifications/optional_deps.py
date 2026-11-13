#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures every module works, or fails clearly, when no optional dependencies are installed.

Our venv always has every extra installed, so nothing here ever runs the way a
customer's minimal install does. In a temporary venv holding every package but
no extras, each shipped module is imported. A module that needs no extra must
import. A module that needs one may fail, but only with an error that tells the
customer which extra to install (smithy-core's ``MissingDependencyError``, or an
``ImportError`` that names the extra); a bare ``No module named 'awscrt'`` leaves
them guessing.
"""

import tempfile
from pathlib import Path

from _common import (
    Finding,
    all_runtime_module_names,
    import_to_dists,
    main,
    make_venv,
    packages,
    probe,
    runtime_modules,
)
from packaging.utils import canonicalize_name


def check() -> list[Finding]:
    findings: list[Finding] = []
    mapping = import_to_dists()
    modules = {m.name: m for m in runtime_modules()}
    with tempfile.TemporaryDirectory(prefix="optional-deps-") as tmp:
        editable = [arg for p in packages() for arg in ("-e", str(p.dir))]
        python = make_venv(Path(tmp) / "venv", *editable)
        reports = probe(all_runtime_module_names(), python)
    for name, report in sorted(reports.items()):
        if report["ok"]:
            continue
        module = modules[name]
        assert module.package is not None  # noqa: S101
        error = report["error"]
        missing = (error.get("missing") or "").split(".")[0]
        dists = {canonicalize_name(d) for d in mapping.get(missing, set())}
        extras = sorted(
            extra
            for extra, reqs in module.package.extras.items()
            if dists & {canonicalize_name(r.name) for r in reqs}
        )
        if not extras:
            findings.append(
                Finding(
                    f"{name} fails without extras: {error['type']}: {error['message']}",
                    module.path,
                    crash=True,
                )
            )
            continue
        message = error["message"]
        clear = error["type"] == "MissingDependencyError" or any(
            e in message for e in extras
        )
        if not clear:
            findings.append(
                Finding(
                    f"{name} needs extra {'/'.join(extras)} but fails with an unclear "
                    f"{error['type']}: {message}",
                    module.path,
                )
            )
    return findings


if __name__ == "__main__":
    main("optional dependencies", check)
