#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures importing a shipped module changes no process-global state.

A library is imported into someone else's process. Configuring logging, reading
or writing environment variables, starting threads, installing warning filters,
signal handlers or excepthooks at import time overrides the application's own
choices, makes behavior depend on import order, and freezes configuration before
the application has set it. Environment access is attributed to the source line
in our code that made it, and warning filters a dependency installs itself are
not ours; the rest is attributed to the imported module.
"""

from _common import Finding, main, probe, runtime_modules


def check() -> list[Finding]:
    findings: list[Finding] = []
    modules = runtime_modules()
    reports = probe(m.name for m in modules)
    # An effect appears for every module that transitively imports its cause;
    # the importer pulling in the fewest new modules is closest to the cause.
    culprits: dict[tuple[str, str, str | None], tuple[int, str, int]] = {}
    for module in modules:
        report = reports[module.name]
        for effect in report["side_effects"]:
            key = (effect["kind"], effect["detail"], effect["where"])
            weight = report.get("new_modules", 0)
            best = culprits.get(key)
            if best is None or weight < best[0]:
                culprits[key] = (weight, module.name, (best[2] + 1) if best else 1)
            else:
                culprits[key] = (best[0], best[1], best[2] + 1)
    paths = {m.name: m.path for m in modules}
    for (kind, detail, where), (_, name, count) in sorted(
        culprits.items(), key=lambda i: i[1][1]
    ):
        located = f" at {where}" if where else ""
        findings.append(
            Finding(
                f"importing {name}: {kind} {detail}{located} (seen from {count} module(s))",
                paths[name],
            )
        )
    return findings


if __name__ == "__main__":
    main("import side effects", check)
