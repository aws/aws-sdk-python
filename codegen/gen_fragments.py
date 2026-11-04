#!/usr/bin/env python3
"""Write a codegen sync changelog fragment for every generated client.

Usage: python codegen/gen_fragments.py
  Only for a smithy-python pointer move; the text comes from CODEGEN_SYNC_CHANGELOG.md
  in the repo root.
"""

import json
import re
import sys
import time
import tomllib
from pathlib import Path

CODEGEN_DIR = Path(__file__).resolve().parent
REPO = CODEGEN_DIR.parent
CLIENTS = REPO / "clients"
MODELS = CODEGEN_DIR / "aws-models"
POINTER = CODEGEN_DIR / "smithy-python.toml"
SYNC_CHANGELOG = REPO / "CODEGEN_SYNC_CHANGELOG.md"
SMITHY_PYTHON_COMMITS = "https://github.com/smithy-lang/smithy-python/commits"
# An older file is assumed to be left over from a previous sync.
SYNC_CHANGELOG_MAX_AGE_SECONDS = 8 * 60 * 60


def main() -> None:
    previous, commit = _pointer_commits()
    description = _description(previous, commit)
    for name in _generated_clients():
        _write_fragment(name, commit, description)


def _pointer_commits() -> tuple[str, str]:
    with POINTER.open("rb") as f:
        pointer = tomllib.load(f)
    commits = []
    for key in ("previous_commit", "commit"):
        value = pointer.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}", value):
            sys.exit(
                f"{POINTER}: {key} must be a full 40-character hash, got {value!r}"
            )
        commits.append(value)
    previous, commit = commits
    if previous == commit:
        sys.exit(f"{POINTER}: previous_commit and commit must differ")
    return previous, commit


def _description(previous: str, commit: str) -> str:
    changes = f"{SMITHY_PYTHON_COMMITS}/{previous}..{commit}"
    reminder = f"write the changelog text for this codegen sync of {changes}"
    if not SYNC_CHANGELOG.exists():
        SYNC_CHANGELOG.touch()
        sys.exit(f"created empty {SYNC_CHANGELOG}; {reminder}")
    age = time.time() - SYNC_CHANGELOG.stat().st_mtime
    if age > SYNC_CHANGELOG_MAX_AGE_SECONDS:
        sys.exit(f"{SYNC_CHANGELOG} is {age / 3600:.1f} hours old; {reminder}")
    text = SYNC_CHANGELOG.read_text().strip()
    if not text:
        sys.exit(f"{SYNC_CHANGELOG} is empty; {reminder}")
    link = f"[smithy-python {previous[:7]}..{commit[:7]}]({changes})"
    return f"Codegen sync for {link}: {text}"


def _generated_clients() -> list[str]:
    return [f"aws-sdk-{model.stem}" for model in sorted(MODELS.glob("*.json"))]


def _write_fragment(name: str, commit: str, description: str) -> None:
    # Keyed by target commit: a rerun for the same pin overwrites, a later sync adds.
    fragment = (
        CLIENTS
        / name
        / ".changes"
        / "next-release"
        / f"{name}-enhancement-codegen-sync-{commit}.json"
    )
    fragment.parent.mkdir(parents=True, exist_ok=True)
    entry = {"type": "enhancement", "description": description}
    fragment.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"wrote {fragment}")


if __name__ == "__main__":
    main()
