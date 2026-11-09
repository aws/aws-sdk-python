#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Checks that the aws-sdk-python meta-package matches the repository's clients.

Each client under ``clients/`` must have:
  - an extra named after its module suffix pinning ``<module>~=<client version>``,
  - an entry in the ``all`` extra,
  - an editable ``[tool.uv.sources]`` path, so a version bump that is not yet on
    PyPI still resolves.

The meta-package must not reference anything that is not a client in the repo.
"""

import sys
import tomllib
from pathlib import Path

META_PACKAGE = "aws-sdk-python"
CLIENT_PREFIX = "aws-sdk-"
ALL_EXTRA = "all"


def main() -> int:
    clients_dir = Path(__file__).resolve().parents[2] / "clients"
    meta = _load(clients_dir / META_PACKAGE / "pyproject.toml")
    clients = {
        p.parent.name: _load(p)["project"]["version"]
        for p in sorted(clients_dir.glob(f"{CLIENT_PREFIX}*/pyproject.toml"))
        if p.parent.name != META_PACKAGE
    }

    errors = [
        *_check_extras(meta["project"].get("optional-dependencies", {}), clients),
        *_check_sources(meta.get("tool", {}).get("uv", {}).get("sources", {}), clients),
    ]
    for error in errors:
        print(f"{META_PACKAGE}: {error}")
    print(f"meta-package: {len(errors)} error(s).")
    return 1 if errors else 0


def _check_extras(extras: dict[str, list[str]], clients: dict[str, str]) -> list[str]:
    errors = []
    expected = {_extra(name): name for name in clients}

    for extra, name in sorted(expected.items()):
        want = [f"{_module(name)}~={clients[name]}"]
        got = extras.get(extra)
        if got is None:
            errors.append(f"missing extra {extra} = {want}")
        elif got != want:
            errors.append(f"extra {extra} is {got}, expected {want}")

    for extra in sorted(set(extras) - set(expected) - {ALL_EXTRA}):
        errors.append(f"extra {extra} has no client in clients/")

    want_all = sorted(f"aws_sdk_python[{extra}]" for extra in expected)
    got_all = sorted(extras.get(ALL_EXTRA, []))
    for item in sorted(set(want_all) - set(got_all)):
        errors.append(f"extra {ALL_EXTRA} is missing {item}")
    for item in sorted(set(got_all) - set(want_all)):
        errors.append(f"extra {ALL_EXTRA} lists {item}, which has no client")
    return errors


def _check_sources(sources: dict[str, object], clients: dict[str, str]) -> list[str]:
    errors = []
    for name in sorted(clients):
        want = {"path": f"../{name}", "editable": True}
        got = sources.get(name)
        if got is None:
            errors.append(f"missing [tool.uv.sources] {name} = {want}")
        elif got != want:
            errors.append(f"[tool.uv.sources] {name} is {got}, expected {want}")
    for name in sorted(set(sources) - set(clients)):
        errors.append(f"[tool.uv.sources] {name} has no client in clients/")
    return errors


def _extra(name: str) -> str:
    return name.removeprefix(CLIENT_PREFIX).replace("-", "_")


def _module(name: str) -> str:
    return name.replace("-", "_")


def _load(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


if __name__ == "__main__":
    sys.exit(main())
