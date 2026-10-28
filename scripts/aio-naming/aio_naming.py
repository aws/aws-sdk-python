#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Enforces aio naming and separation in package source trees.

A package source root is each directory under a ``src`` directory. Its optional
``aio`` subfolder holds all async code; everything else must be sync.

Inside ``<root>/aio``:
  - classes must have at least one async method, own or inherited, and public
    ones must be named ``Async*``.
  - public functions (not methods) must be async and be named ``*_async``; an
    ``async_*`` name is accepted with a warning.

Outside it:
  - public classes must not be named ``Async*``.
  - functions and methods must not be named ``async_*`` or ``*_async``.
  - no ``async def``.

A symbol is private when its name, an enclosing class, or a module path segment
is ``_``-prefixed, or it is nested in a function.
"""

import argparse
import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SRC_GLOBS = ("packages/*/src", "clients/*/src")
AIO = "aio"

_ASYNC_CLASS = re.compile(r"^_*Async(?=[A-Z0-9_]|$)")

type _Def = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    col: int
    severity: Literal["error", "warning"]
    message: str

    def __str__(self) -> str:
        try:
            shown = self.path.relative_to(ROOT)
        except ValueError:
            shown = self.path
        return f"{shown}:{self.line}:{self.col}: {self.severity}: {self.message}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforces aio naming and separation.")
    parser.add_argument(
        "src_dirs",
        nargs="*",
        type=Path,
        help=f"src directories to check (default: {', '.join(DEFAULT_SRC_GLOBS)})",
    )
    args = parser.parse_args()

    src_dirs: list[Path] = args.src_dirs or sorted(
        p for pattern in DEFAULT_SRC_GLOBS for p in ROOT.glob(pattern) if p.is_dir()
    )
    findings = check([src.resolve() for src in src_dirs])

    for finding in findings:
        sys.stdout.write(f"{finding}\n")
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    sys.stderr.write(f"aio naming: {errors} error(s), {warnings} warning(s).\n")
    return 1 if errors else 0


def check(src_dirs: list[Path]) -> list[Finding]:
    """Checks all package source roots under the given src directories."""
    findings: list[Finding] = []
    modules: list[_Module] = []
    for src in src_dirs:
        for root in sorted(p for p in src.iterdir() if _is_source_dir(p)):
            findings.extend(_misplaced_aio(root))
            for path in sorted(root.rglob("*.py")):
                if "__pycache__" in path.relative_to(root).parts:
                    continue
                try:
                    modules.append(_Module.load(root, path))
                except SyntaxError as e:
                    findings.append(
                        Finding(
                            path,
                            e.lineno or 0,
                            e.offset or 0,
                            "error",
                            f"syntax: {e.msg}",
                        )
                    )

    index = _Index(modules)
    for module in modules:
        checker = (_AioChecker if module.in_aio else _SyncChecker)(module, index)
        checker.visit_body(module.tree.body, in_class=False, private=module.private)
        findings.extend(checker.findings)
    return findings


@dataclass
class _Module:
    name: str
    path: Path
    tree: ast.Module
    in_aio: bool
    private: bool
    classes: dict[str, ast.ClassDef] = field(default_factory=dict[str, ast.ClassDef])
    # Bound name -> (source module, attribute); attribute is None for `import x`.
    imports: dict[str, tuple[str, str | None]] = field(
        default_factory=dict[str, tuple[str, str | None]]
    )

    @classmethod
    def load(cls, root: Path, path: Path) -> "_Module":
        rel = path.relative_to(root)
        parts = [root.name, *rel.parts[:-1]]
        if path.stem != "__init__":
            parts.append(path.stem)
        module = cls(
            name=".".join(parts),
            path=path,
            tree=ast.parse(path.read_bytes(), filename=str(path)),
            in_aio=rel.parts[0] == AIO,
            private=any(p.startswith("_") for p in parts),
        )
        module._index_classes()
        module._index_imports(is_package=path.stem == "__init__")
        return module

    def _index_classes(self) -> None:
        stack: list[ast.AST] = list(self.tree.body)
        while stack:
            match node := stack.pop():
                case ast.ClassDef():
                    self.classes.setdefault(node.name, node)
                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    pass
                case _:
                    stack.extend(ast.iter_child_nodes(node))

    def _index_imports(self, *, is_package: bool) -> None:
        for node in ast.walk(self.tree):
            match node:
                case ast.Import():
                    for alias in node.names:
                        if alias.asname:
                            self.imports[alias.asname] = (alias.name, None)
                        else:
                            head = alias.name.split(".")[0]
                            self.imports[head] = (head, None)
                case ast.ImportFrom():
                    source = self._absolute(node, is_package=is_package)
                    for alias in node.names:
                        self.imports[alias.asname or alias.name] = (source, alias.name)
                case _:
                    pass

    def _absolute(self, node: ast.ImportFrom, *, is_package: bool) -> str:
        if not node.level:
            return node.module or ""
        parts = self.name.split(".")
        if not is_package:
            parts = parts[:-1]
        parts = parts[: len(parts) - (node.level - 1)]
        if node.module:
            parts.append(node.module)
        return ".".join(parts)


class _Index:
    def __init__(self, modules: list[_Module]) -> None:
        self._modules = {m.name: m for m in modules}
        self._async: dict[int, bool] = {}

    def is_async(self, module: _Module, cls: ast.ClassDef) -> bool:
        key = id(cls)
        if key not in self._async:
            # Seeded False so an inheritance cycle terminates.
            self._async[key] = False
            self._async[key] = any(
                isinstance(m, ast.AsyncFunctionDef) for m in _methods(cls)
            ) or any(self._base_is_async(module, base) for base in cls.bases)
        return self._async[key]

    def _base_is_async(self, module: _Module, base: ast.expr) -> bool:
        if isinstance(base, ast.Subscript):
            base = base.value
        match base:
            case ast.Name():
                origin = module.imports.get(base.id)
                found = self._lookup(module.name, base.id)
                origin_module = origin[0] if origin else None
            case ast.Attribute():
                origin_module = self._dotted(module, base.value)
                found = (
                    self._lookup(origin_module, base.attr) if origin_module else None
                )
            case _:
                return False
        if found is not None:
            return self.is_async(*found)
        # A base from an unscanned package counts as async if it lives under aio.
        return (
            origin_module is not None
            and origin_module not in self._modules
            and AIO in origin_module.split(".")
        )

    def _lookup(
        self, module_name: str, name: str, depth: int = 0
    ) -> tuple[_Module, ast.ClassDef] | None:
        module = self._modules.get(module_name)
        if module is None or depth > 16:
            return None
        if (cls := module.classes.get(name)) is not None:
            return module, cls
        source = module.imports.get(name)
        if source is None or source[1] is None:
            return None
        return self._lookup(source[0], source[1], depth + 1)

    def _dotted(self, module: _Module, expr: ast.expr) -> str | None:
        match expr:
            case ast.Name():
                source = module.imports.get(expr.id)
                if source is None:
                    return None
                return source[0] if source[1] is None else f"{source[0]}.{source[1]}"
            case ast.Attribute():
                parent = self._dotted(module, expr.value)
                return f"{parent}.{expr.attr}" if parent else None
            case _:
                return None


class _Checker:
    def __init__(self, module: _Module, index: _Index) -> None:
        self.module = module
        self.index = index
        self.findings: list[Finding] = []

    def visit_body(
        self, nodes: list[ast.stmt], *, in_class: bool, private: bool
    ) -> None:
        for node in nodes:
            self._visit(node, in_class=in_class, private=private)

    def check_class(self, node: ast.ClassDef, *, private: bool) -> None:
        raise NotImplementedError

    def check_def(self, node: _Def, *, is_method: bool, private: bool) -> None:
        raise NotImplementedError

    def _visit(self, node: ast.AST, *, in_class: bool, private: bool) -> None:
        match node:
            case ast.ClassDef():
                private = private or node.name.startswith("_")
                self.check_class(node, private=private)
                self.visit_body(node.body, in_class=True, private=private)
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                private = private or node.name.startswith("_")
                self.check_def(node, is_method=in_class, private=private)
                # Nested symbols are unreachable from outside, hence private.
                self.visit_body(node.body, in_class=False, private=True)
            case _:
                for child in ast.iter_child_nodes(node):
                    self._visit(child, in_class=in_class, private=private)

    def _report(
        self, node: ast.stmt, severity: Literal["error", "warning"], message: str
    ) -> None:
        self.findings.append(
            Finding(
                self.module.path, node.lineno, node.col_offset + 1, severity, message
            )
        )


class _AioChecker(_Checker):
    def check_class(self, node: ast.ClassDef, *, private: bool) -> None:
        if not private and not _ASYNC_CLASS.match(node.name):
            self._report(
                node, "error", f"aio class '{node.name}' must start with Async"
            )
        if not self.index.is_async(self.module, node):
            self._report(
                node, "error", f"aio class '{node.name}' must have an async method"
            )

    def check_def(self, node: _Def, *, is_method: bool, private: bool) -> None:
        if is_method or private:
            return
        if not isinstance(node, ast.AsyncFunctionDef):
            self._report(node, "error", f"aio function '{node.name}' must be async")
        bare = node.name.lstrip("_")
        if bare.endswith("_async"):
            return
        if bare.startswith("async_"):
            self._report(
                node,
                "warning",
                f"aio function '{node.name}' should end with _async, not start with async_",
            )
        else:
            self._report(
                node, "error", f"aio function '{node.name}' must end with _async"
            )


class _SyncChecker(_Checker):
    def check_class(self, node: ast.ClassDef, *, private: bool) -> None:
        if not private and _ASYNC_CLASS.match(node.name):
            self._report(
                node, "error", f"non-aio class '{node.name}' must not start with Async"
            )

    def check_def(self, node: _Def, *, is_method: bool, private: bool) -> None:
        kind = "method" if is_method else "function"
        if isinstance(node, ast.AsyncFunctionDef):
            self._report(
                node, "error", f"non-aio {kind} '{node.name}' must not be async"
            )
        bare = node.name.lstrip("_")
        if bare.startswith("async_") or bare.endswith("_async"):
            self._report(
                node,
                "error",
                f"non-aio {kind} '{node.name}' must not start or end with async",
            )


def _misplaced_aio(root: Path) -> Iterator[Finding]:
    for directory in sorted(p for p in root.rglob(AIO) if p.is_dir()):
        if directory.parent != root:
            yield Finding(
                directory,
                0,
                0,
                "error",
                f"'{AIO}' folder must be at the package source root {root.name}/",
            )


def _methods(cls: ast.ClassDef) -> Iterator[_Def]:
    """Defs owned by the class body, including those under if/try blocks."""
    stack: list[ast.AST] = list(cls.body)
    while stack:
        match node := stack.pop():
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                yield node
            case ast.ClassDef():
                pass
            case _:
                stack.extend(ast.iter_child_nodes(node))


def _is_source_dir(path: Path) -> bool:
    return path.is_dir() and path.name != "__pycache__" and "." not in path.name


if __name__ == "__main__":
    sys.exit(main())
