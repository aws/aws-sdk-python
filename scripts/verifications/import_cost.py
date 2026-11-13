#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Records how many of our modules each top-level package pulls in on import, and fails when that changes.

Import cost is paid on every cold start: every Lambda invocation that lands on a
new sandbox, every CLI run, every short-lived worker. It grows one convenient
import at a time, and nobody notices until it shows up as latency. The count of
our own modules loaded is fixed by our code alone, so it is snapshotted in
import-cost.json and any change must be reviewed like the API snapshot. Stdlib
and third-party module counts and wall time vary with dependency versions,
platform and host, so they are printed alongside but not gated. Our native
extensions are blocked so every host measures the same pure-Python fallback,
whether or not it has a compiled build.
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from _common import (
    HERE,
    Finding,
    main,
    owned_roots,
    packages,
    public_runtime_module_names,
    run,
)

SNAPSHOT = HERE / "import-cost.json"
_SCRIPT = """
import importlib, importlib.machinery as machinery, sys, time

roots = set(sys.argv[1].split(","))


class BlockNative:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] not in roots:
            return None
        spec = machinery.PathFinder.find_spec(name, path)
        if spec and spec.origin and spec.origin.endswith(tuple(machinery.EXTENSION_SUFFIXES)):
            raise ImportError(name)
        return None


sys.meta_path.insert(0, BlockNative())
before = set(sys.modules)
start = time.perf_counter()
for m in sys.argv[2:]:
    importlib.import_module(m)
elapsed = time.perf_counter() - start
new = set(sys.modules) - before
ours = sum(m.split(".")[0] in roots for m in new)
print(ours, len(new) - ours, elapsed)
"""


def check() -> list[Finding]:
    findings: list[Finding] = []
    counts: dict[str, int] = {}
    public = public_runtime_module_names()
    roots = ",".join(sorted(owned_roots()))
    scenarios: dict[str, list[str]] = {}
    for package in packages():
        for root in package.roots:
            # The root alone is often a thin facade; customers import submodules.
            scenarios[root] = [root]
            scenarios[f"{root} (all public modules)"] = [
                m for m in public if m.split(".")[0] == root
            ]
    # Wall times are informational, so measuring in parallel only adds noise to them.
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        results = pool.map(lambda t: _measure(roots, t), scenarios.values())
        for label, measured in zip(scenarios, results, strict=True):
            if isinstance(measured, str):
                findings.append(Finding(f"import {label} failed: {measured}"))
                continue
            counts[label], others, fastest = measured
            findings.append(
                Finding(
                    f"{label}: {counts[label]} of our modules, {others} other modules, "
                    f"{fastest * 1000:.1f} ms",
                    severity="info",
                )
            )
    SNAPSHOT.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n")
    tracked = run(["git", "ls-files", "--error-unmatch", str(SNAPSHOT)]).returncode == 0
    if not tracked:
        findings.append(
            Finding(
                "import-cost.json created; commit it as the baseline",
                SNAPSHOT,
                severity="warning",
            )
        )
    elif run(["git", "diff", "--quiet", "--", str(SNAPSHOT)]).returncode:
        diff = run(["git", "--no-pager", "diff", "--", str(SNAPSHOT)]).stdout
        findings.append(
            Finding(
                f"import module counts changed; review and commit:\n{diff}", SNAPSHOT
            )
        )
    return findings


def _measure(roots: str, targets: list[str]) -> tuple[int, int, float] | str:
    """Our and other new module counts and the fastest of three wall times, or the error output."""
    samples: list[tuple[int, int, float]] = []
    for _ in range(3):
        proc = run([sys.executable, "-c", _SCRIPT, roots, *targets])
        if proc.returncode != 0:
            return proc.stderr.strip()[-300:]
        ours, others, elapsed = proc.stdout.split()
        samples.append((int(ours), int(others), float(elapsed)))
    return samples[0][0], samples[0][1], min(s[2] for s in samples)


if __name__ == "__main__":
    main("import cost", check)
