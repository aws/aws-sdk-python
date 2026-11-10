#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures importing any shipped module emits no deprecation warnings.

A deprecation warning at import time is a removal already scheduled for a future
Python or dependency release. Customers who run with warnings as errors (common
in test suites) break immediately, and everyone else breaks on the release that
removes the API. Each module is imported in a fresh interpreter so the warning is
attributed to the module that triggers it.
"""

from _common import Finding, main, probe, runtime_modules

_CATEGORIES = frozenset(
    {"DeprecationWarning", "PendingDeprecationWarning", "FutureWarning"}
)


def check() -> list[Finding]:
    findings: list[Finding] = []
    modules = runtime_modules()
    reports = probe(m.name for m in modules)
    seen: set[tuple[str, str]] = set()
    for module in modules:
        for warning in reports[module.name]["warnings"]:
            if warning["category"] not in _CATEGORIES:
                continue
            key = (warning["where"], warning["message"])
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    f"importing {module.name}: {warning['category']} at {warning['where']}: "
                    f"{warning['message']}",
                    module.path,
                )
            )
    return findings


if __name__ == "__main__":
    main("import deprecations", check)
