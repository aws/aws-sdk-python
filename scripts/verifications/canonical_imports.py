#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures our own code imports each of our symbols from the module that defines it.

Importing through a re-export makes the importer depend on the re-exporting
module's import order and contents, which is how import cycles and accidental
public-surface dependencies creep in. It also hides where a symbol lives from
readers and refactoring tools. A re-export import is accepted under a private
local name (``import X as _X``), which marks it as a deliberate, module-internal
choice, and when the defining module is private, since the re-export is then the
symbol's public home. An import from another package's root is also accepted
when that root lists the symbol in ``__all__``, since the root's declared
surface is that package's public contract.

Covers generated client and hand-written package sources.
"""

from _common import (
    Finding,
    canonical_definition,
    main,
    module_index,
    owned_roots,
    resolve_from,
    runtime_modules,
)


def check() -> list[Finding]:
    findings: list[Finding] = []
    index = module_index()
    roots = owned_roots()
    for module in runtime_modules():
        for imp in module.imports:
            if imp.name is None or imp.name == "*" or imp.top not in roots:
                continue
            target, attr = resolve_from(imp)
            if attr is None:
                continue
            source = index.get(target)
            if source is None:
                findings.append(
                    Finding(
                        f"cannot resolve module {target}",
                        module.path,
                        imp.line,
                        "warning",
                    )
                )
                continue
            if source.model_data or attr in source.defined:
                continue
            if imp.asname is not None and imp.asname.startswith("_"):
                continue
            canonical = canonical_definition(target, attr)
            if canonical is None:
                findings.append(
                    Finding(
                        f"{attr} is not defined or imported in {target}",
                        module.path,
                        imp.line,
                        "warning",
                    )
                )
                continue
            if any(part.startswith("_") for part in canonical.split(".")):
                continue
            if _is_declared_package_export(
                module.name, target, attr, source.dunder_all
            ):
                continue
            findings.append(
                Finding(
                    f"imports {attr} from re-exporting {target}; defined in {canonical}",
                    module.path,
                    imp.line,
                )
            )
    return findings


def _is_declared_package_export(
    importer: str, target: str, attr: str, dunder_all: list[str] | None
) -> bool:
    """Whether target is another package's root and lists attr in its __all__."""
    return (
        "." not in target
        and importer.split(".")[0] != target
        and dunder_all is not None
        and attr in dunder_all
    )


if __name__ == "__main__":
    main("canonical imports", check)
