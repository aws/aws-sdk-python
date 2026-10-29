#!/usr/bin/env python3
"""Regenerate aws-sdk-python clients from service models via smithy-python codegen.

Usage: python codegen/gen_client.py (--all | <name>...) [--pinned] [--batch-size N]
  <name> accepts dynamodb, aws_sdk_dynamodb, aws-sdk-dynamodb, or bedrock-runtime forms.
  --pinned builds codegen from the smithy-python commit in codegen/smithy-python.toml;
  without it, the codegen last published to the local Maven cache is used.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

CODEGEN_DIR = Path(__file__).resolve().parent
REPO = CODEGEN_DIR.parent
MODELS = CODEGEN_DIR / "aws-models"
CLIENTS = REPO / "clients"
OVERLAYS = REPO / "scripts" / "client-overlays"
PROJECT = "aws-sdk-python-codegen"
META_PACKAGE = "aws-sdk-python"
DEFAULT_BATCH_SIZE = 25
POINTER = CODEGEN_DIR / "smithy-python.toml"
PINNED_DIR = CODEGEN_DIR / ".smithy-python"

# Paths codegen never emits; they survive the pre-generation delete. A path codegen
# does emit but that must differ from codegen output belongs in client-overlays.
KEEP = (
    ".changes",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE",
    "Makefile",
    "docs",
    "examples",
    "scripts",
    "tests/integration",
    "zensical.toml",
)

# The integration tests of these clients set up resources with boto3.
CLIENTS_REQUIRING_BOTO3 = {
    "aws-sdk-connecthealth",
    "aws-sdk-lex-runtime-v2",
    "aws-sdk-transcribe-streaming",
}
CLIENT_DOC_DEPS = {"zensical", "mkdocstrings[python]"}


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("names", nargs="*", default=[])
    parser.add_argument("-b", "--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--pinned", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        sys.exit("--batch-size must be at least 1")

    models = (
        sorted(MODELS.glob("*.json"))
        if args.all
        else [resolve_model(n) for n in args.names]
    )
    if not models:
        sys.exit("no clients selected")

    if args.pinned:
        with _pinned_codegen(_pinned_commit()) as gradle_args:
            _generate(models, args.batch_size, gradle_args)
    else:
        _generate(models, args.batch_size, [])


def _generate(models: list[Path], batch_size: int, gradle_args: list[str]) -> None:
    docs_deps = _docs_deps()
    for start in range(0, len(models), batch_size):
        batch = models[start : start + batch_size]
        _build(batch, gradle_args)
        for model in batch:
            _install_client(model.stem, docs_deps)


def _pinned_commit() -> str:
    with POINTER.open("rb") as f:
        commit = tomllib.load(f)["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        sys.exit(f"{POINTER}: commit must be a full 40-character hash, got {commit!r}")
    return commit


@contextmanager
def _pinned_codegen(commit: str) -> Iterator[list[str]]:
    colocated = _smithy_python()
    if not (colocated / ".git").exists():
        sys.exit(f"no smithy-python checkout at {colocated}")
    git = ["git", "-C", str(colocated)]
    if subprocess.run([*git, "cat-file", "-e", f"{commit}^{{commit}}"]).returncode:
        subprocess.run([*git, "fetch", "origin", commit], check=True)

    worktree = PINNED_DIR / commit
    subprocess.run([*git, "worktree", "prune"], check=True)
    if worktree.exists():
        subprocess.run(
            [*git, "worktree", "remove", "--force", str(worktree)], check=True
        )
    subprocess.run(
        [*git, "worktree", "add", "--detach", str(worktree), commit], check=True
    )

    # Every develop commit carries the same nominal version, so a shared ~/.m2 is
    # last-publish-wins; a private repo guarantees the jars come from this commit.
    m2 = PINNED_DIR / "m2"
    gradle_args = [f"-Dmaven.repo.local={m2}"]
    previous = os.environ.get("SMITHY_PYTHON")
    os.environ["SMITHY_PYTHON"] = str(worktree)
    try:
        marker = m2 / "smithy-python-commit"
        if not (marker.exists() and marker.read_text() == commit):
            print(f"publishing smithy-python codegen at {commit}")
            codegen = worktree / "codegen"
            subprocess.run(
                [
                    str(codegen / "gradlew"),
                    "-p",
                    str(codegen),
                    *gradle_args,
                    ":core:publishToMavenLocal",
                    ":aws:core:publishToMavenLocal",
                    "-q",
                ],
                check=True,
            )
            marker.write_text(commit)
        yield gradle_args
    finally:
        if previous is None:
            os.environ.pop("SMITHY_PYTHON")
        else:
            os.environ["SMITHY_PYTHON"] = previous
        subprocess.run(
            [*git, "worktree", "remove", "--force", str(worktree)], check=True
        )


def _smithy_python() -> Path:
    return Path(
        os.environ.get("SMITHY_PYTHON", REPO.parent / "smithy-python")
    ).resolve()


def resolve_model(name: str) -> Path:
    key = name.strip()
    for prefix in ("aws-sdk-", "aws_sdk_"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
            break
    for cand in {key, key.replace("_", "-"), key.replace("-", "_")}:
        model = MODELS / f"{cand}.json"
        if model.exists():
            return model
    available = sorted(p.stem for p in MODELS.glob("*.json"))
    sys.exit(f"no model for '{name}' in {MODELS}\navailable: {', '.join(available)}")


def service_id(model: Path) -> str:
    shapes = json.loads(model.read_text())["shapes"]
    services = [k for k, v in shapes.items() if v.get("type") == "service"]
    if len(services) != 1:
        sys.exit(
            f"expected exactly one service shape in {model.name}, found {services}"
        )
    return services[0]


def _projection(model: Path) -> dict[str, object]:
    slug = model.stem
    # Per-projection imports make each client's input independent of its batch.
    return {
        "imports": [str(model)],
        "plugins": {
            "python-client-codegen": {
                "service": service_id(model),
                "module": _module(slug),
                "moduleVersion": _client_version(slug),
            }
        },
    }


def _module(slug: str) -> str:
    return "aws_sdk_" + slug.replace("-", "_")


def _client_version(slug: str) -> str:
    pyproject = CLIENTS / f"aws-sdk-{slug}" / "pyproject.toml"
    if pyproject.exists():
        return _read_version(pyproject)
    # As in the release build: clients share major.minor, so a new one starts at .0.
    for existing in sorted(CLIENTS.glob("aws-sdk-*/pyproject.toml")):
        if existing.parent.name != META_PACKAGE:
            major, minor, _ = _read_version(existing).split(".")
            return f"{major}.{minor}.0"
    sys.exit("cannot determine a version for new client: no existing client has one")


def _read_version(pyproject: Path) -> str:
    with pyproject.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _build(models: list[Path], gradle_args: list[str]) -> None:
    build_config = {
        "version": "1.0",
        "projections": {m.stem: _projection(m) for m in models},
    }
    build_file = CODEGEN_DIR / "smithy-build.json"
    build_file.write_text(json.dumps(build_config, indent=4) + "\n")
    print(f"generating {len(models)} client(s): {', '.join(m.stem for m in models)}")
    subprocess.run(
        [
            str(CODEGEN_DIR / "gradlew"),
            "-p",
            str(CODEGEN_DIR),
            *gradle_args,
            "clean",
            "build",
            "-q",
        ],
        check=True,
    )


def _install_client(slug: str, docs_deps: list[str]) -> None:
    name = f"aws-sdk-{slug}"
    projection = (
        CODEGEN_DIR
        / "build"
        / "smithyprojections"
        / PROJECT
        / slug
        / "python-client-codegen"
    )
    if not projection.is_dir():
        sys.exit(f"codegen produced no output at {projection}")
    generated = _relative_files(projection)
    _check_keep_untouched(name, generated)
    overlays = _overlay_files(name, generated)

    dest = CLIENTS / name
    _clear(dest)
    shutil.copytree(projection, dest, dirs_exist_ok=True)
    for rel in overlays:
        shutil.copyfile(OVERLAYS / name / rel, dest / rel)

    if docs_deps:
        _uv_add(dest, "docs", docs_deps)
    if name in CLIENTS_REQUIRING_BOTO3:
        _uv_add(dest, "test", ["boto3"])
    _format(dest / "src" / _module(slug), dest / "pyproject.toml")
    print(f"wrote {dest}")


def _relative_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def _is_kept(rel: str) -> bool:
    return any(rel == k or rel.startswith(k + "/") for k in KEEP)


def _check_keep_untouched(name: str, generated: set[str]) -> None:
    clashes = sorted(rel for rel in generated if _is_kept(rel))
    if clashes:
        sys.exit(
            f"{name}: codegen now emits kept paths {clashes}; "
            "remove them from KEEP and move any hand edits to scripts/client-overlays"
        )


def _overlay_files(name: str, generated: set[str]) -> list[str]:
    root = OVERLAYS / name
    if not root.is_dir():
        return []
    overlays = sorted(_relative_files(root))
    stray = [rel for rel in overlays if rel not in generated]
    if stray:
        sys.exit(
            f"{name}: overlays {stray} do not replace any generated file; "
            "move them into the client and add them to KEEP"
        )
    return overlays


def _clear(dest: Path) -> None:
    if not dest.exists():
        return
    ignored = _ignored(dest)
    for path in sorted(dest.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        rel = path.relative_to(dest).as_posix()
        if (
            _is_kept(rel)
            or rel in ignored
            or any(rel.startswith(i + "/") for i in ignored)
        ):
            continue
        if path.is_dir() and not path.is_symlink():
            if not any(path.iterdir()):
                path.rmdir()
        else:
            path.unlink()


def _ignored(dest: Path) -> set[str]:
    # Gitignored files (venvs, lockfiles) are local state, not leftover codegen output.
    out = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--directory",
            "-z",
            ".",
        ],
        cwd=dest,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return {p.rstrip("/") for p in out.split("\0") if p}


def _docs_deps() -> list[str]:
    deps = []
    for line in (REPO / "requirements-docs.in").read_text().splitlines():
        line = line.split("#")[0].strip()
        if line and re.split(r"[<>=!~]", line)[0] in CLIENT_DOC_DEPS:
            deps.append(line)
    return deps


def _uv_add(client: Path, group: str, deps: list[str]) -> None:
    subprocess.run(
        ["uv", "add", "--group", group, "--frozen", *deps], cwd=client, check=True
    )


def _format(src_dir: Path, config: Path) -> None:
    # The generator only formats when ruff is on gradle's PATH, which it usually is not.
    smithy_python = _smithy_python()
    if not (smithy_python / "pyproject.toml").exists():
        print(f"skipping ruff: no smithy-python checkout at {smithy_python}")
        return
    cfg = ["--config", str(config)]
    for cmd in (
        ["uv", "run", "ruff", "check", str(src_dir), "--fix", *cfg],
        ["uv", "run", "ruff", "format", str(src_dir), *cfg],
    ):
        subprocess.run(cmd, cwd=smithy_python, check=True)


if __name__ == "__main__":
    main()
