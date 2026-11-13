#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Ensures the Python API surface is reflected in the api.json and api-rex.json files.

All changes to the surface must be intentional and reviewed in the PR making them.

For every public module (no underscore-prefixed path segment), records each
reachable non-underscore symbol that we OWN. Symbols defined in the module's own
source go in api.json. Symbols re-exported from another of our modules (marked
with a ``rex-`` kind prefix) go in api-rex.json. Reachable re-exports of
third-party/stdlib names are excluded: they are not ours to keep stable. Then
fails if writing either file changed it from the committed version, so an
unreviewed surface change cannot pass CI.

Also records the dual-mode symbols, each async symbol under ``aio`` with its sync
twin, in mirrors.txt, which fails the same way when it changes.
"""

import ast
import importlib
import importlib.util
import inspect
import json
import subprocess
import sys
import types
import typing
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA_PATH = HERE / "api.json"
REX_PATH = HERE / "api-rex.json"
MIRRORS_PATH = HERE / "mirrors.txt"
PACKAGES_DIR = ROOT / "packages"

# Top-level module names we own: one per packages/*/src/<module> or
# clients/*/src/<module>. A reachable symbol defined under any of these is ours to
# keep stable; anything else (stdlib, typing, third-party) is excluded from the
# surface. Only packages are recorded, since codegen owns the clients' surface.
_OWNED_ROOTS = frozenset(
    child.name
    for src in [*PACKAGES_DIR.glob("*/src"), *ROOT.glob("clients/*/src")]
    for child in src.iterdir()
    if (child / "__init__.py").exists()
)


def main() -> int:
    for src in sorted(PACKAGES_DIR.glob("*/src")):
        sys.path.insert(0, str(src))

    surface = _collect_surface()
    declared = {
        mod: {n: k for n, k in symbols.items() if not k.startswith("rex-")}
        for mod, symbols in surface.items()
    }
    rex = {
        mod: {n: k for n, k in symbols.items() if k.startswith("rex-")}
        for mod, symbols in surface.items()
    }
    # api.json keeps every public module, even one with only re-exports, so a
    # removed module still shows up in its diff.
    _write_json(DATA_PATH, declared)
    _write_json(REX_PATH, {mod: symbols for mod, symbols in rex.items() if symbols})
    MIRRORS_PATH.write_text(_mirrors())

    paths = (DATA_PATH, REX_PATH, MIRRORS_PATH)
    changed = [path for path in paths if _changed(path)]
    if changed:
        names = ", ".join(str(path.relative_to(ROOT)) for path in changed)
        print(
            f"\n{names} updated to reflect the current API surface. Review the "
            "change above and commit it in the PR that made it.",
            file=sys.stderr,
        )
        return 1
    print("API snapshot is up to date.")
    return 0


def _write_json(path: Path, surface: dict[str, dict[str, str]]) -> None:
    ordered = {k: dict(sorted(v.items())) for k, v in sorted(surface.items())}
    path.write_text(json.dumps(ordered, indent=2) + "\n")


def _collect_surface() -> dict[str, dict[str, str]]:
    surface: dict[str, dict[str, str]] = {}
    for src in sorted(PACKAGES_DIR.glob("*/src")):
        for modname in _public_module_paths(src):
            surface[modname] = _module_surface(modname)
    return surface


def _public_module_paths(src: Path) -> list[str]:
    # A module path is public only when every segment is non-underscore; a single
    # `_private`/`_foo` segment anywhere makes the whole subtree private.
    paths: set[str] = set()
    for init in src.rglob("__init__.py"):
        parts = init.parent.relative_to(src).parts
        if parts and not any(seg.startswith("_") for seg in parts):
            paths.add(".".join(parts))
    for py in src.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        parts = py.relative_to(src).with_suffix("").parts
        if not any(seg.startswith("_") for seg in parts):
            paths.add(".".join(parts))
    return sorted(paths)


def _module_surface(modname: str) -> dict[str, str]:
    module = importlib.import_module(modname)
    defined = _defined_here(modname)
    surface: dict[str, str] = {}
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if name in defined:
            # Defined in this module's own source: our surface, plain kind.
            surface[name] = _kind(obj)
        elif _is_owned(obj):
            # Reachable here but defined in another of our packages: we own and
            # must track it, but mark it rex (re-export) so the defining module
            # and the re-export are distinguishable.
            surface[name] = f"rex-{_kind(obj)}"
        # else: re-exported third-party/stdlib (Protocol, os, TYPE_CHECKING) --
        # reachable, but not ours to keep stable, so excluded from the surface.
    return surface


def _defined_here(modname: str) -> set[str]:
    # Top-level definitions in this module's own source. AST is the only way to
    # attribute a bare constant (MAX_PAYLOAD_LENGTH = ...) to its defining
    # module: the value object carries no assignment site, and __module__ on an
    # int is "builtins".
    path = _source_path(modname)
    if path is None:
        return set()
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _source_path(modname: str) -> Path | None:
    for src in PACKAGES_DIR.glob("*/src"):
        base = src.joinpath(*modname.split("."))
        for candidate in (base / "__init__.py", base.with_suffix(".py")):
            if candidate.exists():
                return candidate
    return None


def _is_owned(obj: object) -> bool:
    mod = (
        obj.__name__
        if isinstance(obj, types.ModuleType)
        else getattr(obj, "__module__", None)
    )
    return bool(mod) and mod.split(".")[0] in _OWNED_ROOTS


def _kind(obj: object) -> str:
    if isinstance(obj, types.ModuleType):
        return "module"
    if inspect.isclass(obj):
        if getattr(obj, "_is_protocol", False):
            base = "protocol"
        elif issubclass(obj, Exception):
            base = "exception"
        else:
            base = "class"
        return f"{base}[async]" if _has_async_method(obj) else base
    if inspect.iscoroutinefunction(obj):
        return "function[async]"
    if inspect.isfunction(obj) or inspect.isbuiltin(obj) or inspect.ismethod(obj):
        return "function"
    if _is_type_alias(obj):
        return "type_alias"
    if callable(obj):
        return "callable"
    return type(obj).__name__


def _has_async_method(cls: type) -> bool:
    # Reads raw __dict__ values across the MRO rather than getmembers, which would
    # trigger descriptor/property execution on a class not meant to be introspected
    # cold. Unwraps static/classmethod so an `async def` behind either is still seen.
    for klass in getattr(cls, "__mro__", (cls,)):
        for value in vars(klass).values():
            if inspect.iscoroutinefunction(getattr(value, "__func__", value)):
                return True
    return False


def _is_type_alias(obj: object) -> bool:
    # typing.TypeAliasType (`type X = ...`), typing special forms (Literal/Union
    # subscriptions), and PEP 585 builtin generics (`list[int]`) are all exported
    # as type aliases, not runtime values.
    if isinstance(obj, typing.TypeAliasType):
        return True
    if type(obj) is types.GenericAlias:
        return True
    return getattr(obj, "__module__", None) == "typing" and hasattr(obj, "__origin__")


def _mirrors() -> str:
    path = ROOT / "scripts" / "aio-naming" / "aio_naming.py"
    spec = importlib.util.spec_from_file_location("aio_naming", path)
    assert spec is not None and spec.loader is not None  # noqa: S101
    module = importlib.util.module_from_spec(spec)
    # Registered first so the module's dataclasses can resolve their own module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.dual_mode_report()


def _changed(path: Path) -> bool:
    """Whether the file differs from git, counting a new untracked file as changed."""
    # Fixed argv, no shell: git resolved from PATH is the repo's own convention.
    argv = ["git", "diff", "--exit-code", "--", str(path)]
    diff = subprocess.run(argv, cwd=ROOT)  # noqa: S603
    argv = ["git", "ls-files", "--others", "--exclude-standard", "--", str(path)]
    untracked = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)  # noqa: S603
    return diff.returncode != 0 or bool(untracked.stdout.strip())


if __name__ == "__main__":
    raise SystemExit(main())
