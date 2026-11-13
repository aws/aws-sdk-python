#!/usr/bin/env python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Enforces aio naming and separation in package source trees.

A package source root is each directory under a ``src`` directory. Its optional
``aio`` subfolder holds all async code; everything else must be sync.

Inside ``<root>/aio``:
  - classes must be async, and public ones must be named ``Async*``, except the
    transports with no sync twin in ``_NO_TWIN_NAMES``. A class is
    async when it has an async method, own or inherited, or its annotations or
    base class arguments name an ``Async*`` type. A class holding only data (no
    methods besides dunders) also qualifies, since it serves the async code
    beside it.
  - public functions (not methods) must be async and be named ``*_async``; an
    ``async_*`` name is accepted with a warning.

Outside it:
  - no imports from an ``aio`` package, including under ``TYPE_CHECKING``.
  - public classes must not be named ``Async*``.
  - functions and methods must not be named ``async_*`` or ``*_async``.
  - no ``async def``.

Public members a sync twin shares with its aio counterpart must take the same
argument names, so code switching calling styles keeps its keyword arguments.
Members on only one side are allowed, since some capabilities (event streams,
duplex streaming) are async-only by design. Only twins under ``packages/`` are
compared and listed, since generated clients' API is codegen's to keep stable.

A symbol is private when its name, an enclosing class, or a module path segment
is ``_``-prefixed, or it is nested in a function.

Output starts with each public aio symbol that has a sync twin
(``AsyncFoo``/``Foo``, ``foo_async``/``foo``) as a tree by folder, followed by
the findings.
"""

import argparse
import ast
import importlib
import inspect
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES_DIR = ROOT / "packages"
CLIENTS_DIR = ROOT / "clients"
# Hand-written, though it lives beside the generated clients.
METAPACKAGE_DIR = CLIENTS_DIR / "aws-sdk-python"
DEFAULT_SRC_GLOBS = ("packages/*/src", "clients/*/src")
AIO = "aio"

_ASYNC_CLASS = re.compile(r"^_*Async(?=[A-Z0-9_]|$)")

# Sync names that describe async things rather than being async themselves.
_SYNC_ASYNC_NAMES = frozenset({"AsyncBodyError"})

# aio classes with no sync twin that keep their established names.
_NO_TWIN_NAMES = frozenset(
    {
        "AIOHTTPClient",
        "AIOHTTPClientConfig",
        "AWSCRTHTTPClient",
        "AWSCRTHTTPClientConfig",
    }
)

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

    src_dirs: list[Path] = args.src_dirs or _default_src_dirs()
    findings, modules = _load([src.resolve() for src in src_dirs])
    findings.extend(_check_modules(modules))
    findings.extend(_check_parity(modules))
    findings = [_soften(f) for f in findings]

    sys.stdout.write(dual_mode_tree(modules))
    if findings:
        sys.stdout.write("\n")
    for finding in findings:
        sys.stdout.write(f"{finding}\n")
    # Flushed so the summary follows the report even when both streams share a pipe.
    sys.stdout.flush()
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    sys.stderr.write(f"aio naming: {errors} error(s), {warnings} warning(s).\n")
    return 1 if errors else 0


def check(src_dirs: list[Path]) -> list[Finding]:
    """Checks all package source roots under the given src directories."""
    findings, modules = _load(src_dirs)
    found = findings + _check_modules(modules) + _check_parity(modules)
    return [_soften(f) for f in found]


def dual_mode_report() -> str:
    """Render the dual-mode symbol tree for the default package source roots."""
    _, modules = _load([src.resolve() for src in _default_src_dirs()])
    return dual_mode_tree(modules)


def dual_mode_tree(modules: "list[_Module]") -> str:
    """Render the public aio symbols that have a sync twin, as a tree by folder.

    Each aio symbol is listed under its module with its sync twin, which is shown
    with its module when that isn't the aio module's mirror outside ``aio``.
    """
    rows: dict[tuple[str, ...], list[tuple[str, str]]] = {}
    for pair in _twin_pairs(modules):
        mirror = ".".join(p for p in pair.aio.name.split(".") if p != AIO)
        shown = (
            pair.twin
            if pair.sync.name == mirror
            else f"{pair.twin}  ({pair.sync.name})"
        )
        rows.setdefault(_display_path(pair.aio), []).append((pair.name, shown))

    lines = ["Dual-mode symbols (async in aio, sync twin outside):"]
    previous: tuple[str, ...] = ()
    count = 0
    for path in sorted(rows):
        common = 0
        while (
            common < min(len(path), len(previous)) - 1
            and path[common] == previous[common]
        ):
            common += 1
        for depth in range(common, len(path)):
            lines.append("  " * (depth + 1) + path[depth])
        width = max(len(name) for name, _ in rows[path])
        for name, shown in sorted(rows[path]):
            lines.append("  " * (len(path) + 1) + f"{name.ljust(width)}  {shown}")
            count += 1
        previous = path
    lines.append(f"{count} dual-mode symbol(s).")
    return "\n".join(lines) + "\n"


def _default_src_dirs() -> list[Path]:
    return sorted(
        p for pattern in DEFAULT_SRC_GLOBS for p in ROOT.glob(pattern) if p.is_dir()
    )


def _load(src_dirs: list[Path]) -> "tuple[list[Finding], list[_Module]]":
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
    return findings, modules


def _check_modules(modules: "list[_Module]") -> list[Finding]:
    findings: list[Finding] = []
    index = _Index(modules)
    for module in modules:
        checker = (_AioChecker if module.in_aio else _SyncChecker)(module, index)
        checker.visit_body(module.tree.body, in_class=False, private=module.private)
        if not module.in_aio:
            findings.extend(_aio_imports(module))
        findings.extend(checker.findings)
    return findings


def _check_parity(modules: "list[_Module]") -> list[Finding]:
    findings: list[Finding] = []
    for pair in _twin_pairs(modules):
        async_obj = getattr(importlib.import_module(pair.aio.name), pair.name)
        sync_obj = getattr(importlib.import_module(pair.sync.name), pair.twin)
        label = f"{pair.aio.name}.{pair.name} / {pair.sync.name}.{pair.twin}"
        line = next(
            (
                n.lineno
                for n in pair.aio.tree.body
                if isinstance(n, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
                and n.name == pair.name
            ),
            0,
        )
        findings.extend(
            Finding(pair.aio.path, line, 1, "error", message)
            for message in _parity_differences(label, async_obj, sync_obj)
        )
    return findings


@dataclass(frozen=True)
class _TwinPair:
    aio: "_Module"
    name: str
    sync: "_Module"
    twin: str


def _twin_pairs(modules: "list[_Module]") -> Iterator[_TwinPair]:
    """Public aio symbols with a sync twin, preferring the twin in the aio module's mirror."""
    sync_defs: dict[tuple[str, str], list[_Module]] = {}
    for module in modules:
        if module.in_aio or module.private:
            continue
        for name in _public_defs(module):
            sync_defs.setdefault((_root_of(module), name), []).append(module)

    for module in modules:
        if not module.in_aio or module.private:
            continue
        if not module.path.is_relative_to(PACKAGES_DIR):
            continue
        mirror = ".".join(p for p in module.name.split(".") if p != AIO)
        for name in _public_defs(module):
            twin = _sync_name(name)
            if twin is None:
                continue
            candidates = sync_defs.get((_root_of(module), twin))
            if not candidates:
                continue
            found = next((m for m in candidates if m.name == mirror), candidates[0])
            yield _TwinPair(module, name, found, twin)


def _parity_differences(label: str, async_obj: Any, sync_obj: Any) -> list[str]:
    if inspect.isclass(async_obj) and inspect.isclass(sync_obj):
        async_members = _public_members(async_obj)
        sync_members = _public_members(sync_obj)
        messages: list[str] = []
        for name in sorted(async_members.keys() & sync_members.keys()):
            messages += _signature_difference(
                f"{label}.{name}", async_members[name], sync_members[name]
            )
        return messages
    if callable(async_obj) and callable(sync_obj):
        return _signature_difference(label, async_obj, sync_obj)
    return [f"{label}: kinds differ"]


def _public_members(cls: type) -> dict[str, Any]:
    members: dict[str, Any] = {}
    for klass in reversed(cls.__mro__):
        if klass is object or klass.__module__ in ("typing", "abc", "builtins"):
            continue
        for name, value in vars(klass).items():
            if not name.startswith("_"):
                members[name] = value
    return members


def _signature_difference(label: str, async_obj: Any, sync_obj: Any) -> list[str]:
    async_sig, sync_sig = _signature(async_obj), _signature(sync_obj)
    if async_sig is None or sync_sig is None or async_sig == sync_sig:
        return []
    return [f"{label}: argument names differ: async {async_sig} / sync {sync_sig}"]


def _signature(obj: Any) -> tuple[str, ...] | None:
    func = obj.fget if isinstance(obj, property) else getattr(obj, "__func__", obj)
    if not callable(func):
        return None
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return None
    return tuple(
        p.name for p in sig.parameters.values() if p.name not in ("self", "cls")
    )


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
            self._async[key] = (
                any(isinstance(m, ast.AsyncFunctionDef) for m in _methods(cls))
                or any(self._base_is_async(module, base) for base in cls.bases)
                or _names_async_type(cls)
                or _holds_only_data(cls)
            )
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
        if (
            not private
            and not _ASYNC_CLASS.match(node.name)
            and node.name not in _NO_TWIN_NAMES
        ):
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
        if (
            not private
            and _ASYNC_CLASS.match(node.name)
            and node.name not in _SYNC_ASYNC_NAMES
        ):
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
        # A generated client's methods are modeled operations, named by the service.
        if (
            is_method
            and _is_generated(self.module.path)
            and self.module.name.endswith(".client")
        ):
            return
        if bare.startswith("async_") or bare.endswith("_async"):
            self._report(
                node,
                "error",
                f"non-aio {kind} '{node.name}' must not start or end with async",
            )


def _aio_imports(module: "_Module") -> Iterator[Finding]:
    is_package = module.path.stem == "__init__"
    for node in ast.walk(module.tree):
        match node:
            case ast.Import():
                sources = [alias.name for alias in node.names]
            case ast.ImportFrom():
                source = module._absolute(node, is_package=is_package)  # pyright: ignore[reportPrivateUsage]
                # `from pkg import aio` names the aio package itself.
                sources = [f"{source}.{alias.name}" for alias in node.names]
            case _:
                continue
        for source in sources:
            if AIO in source.split("."):
                yield Finding(
                    module.path,
                    node.lineno,
                    node.col_offset + 1,
                    "error",
                    f"non-aio module '{module.name}' must not import '{source}'",
                )
                break


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


_ASYNC_TYPE_NAME = re.compile(r"(?<![A-Za-z0-9])_*Async[A-Z]")


def _names_async_type(cls: ast.ClassDef) -> bool:
    """Whether the class's annotations or base class arguments name an Async* type."""
    exprs: list[ast.expr] = [b.slice for b in cls.bases if isinstance(b, ast.Subscript)]
    for stmt in cls.body:
        if isinstance(stmt, ast.AnnAssign):
            exprs.append(stmt.annotation)
        elif isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            args = stmt.args
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
                if arg.annotation is not None:
                    exprs.append(arg.annotation)
            if stmt.returns is not None:
                exprs.append(stmt.returns)
    for expr in exprs:
        for node in ast.walk(expr):
            text = (
                node.id
                if isinstance(node, ast.Name)
                else node.attr
                if isinstance(node, ast.Attribute)
                else node.value
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
                else None
            )
            if text is not None and _ASYNC_TYPE_NAME.search(text):
                return True
    return False


def _holds_only_data(cls: ast.ClassDef) -> bool:
    return all(m.name.startswith("__") and m.name.endswith("__") for m in _methods(cls))


def _public_defs(module: "_Module") -> list[str]:
    return [
        node.name
        for node in module.tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    ]


def _sync_name(name: str) -> str | None:
    if match := _ASYNC_CLASS.match(name):
        return name[match.end() :]
    if name.endswith("_async"):
        return name.removesuffix("_async")
    return None


def _root_of(module: "_Module") -> str:
    return module.name.split(".")[0]


def _display_path(module: "_Module") -> tuple[str, ...]:
    """Folders then file of a module, e.g. ("smithy_core/", "aio/", "client.py")."""
    parts = module.name.split(".")
    if module.path.stem == "__init__":
        return (*(f"{p}/" for p in parts), "__init__.py")
    return (*(f"{p}/" for p in parts[:-1]), f"{parts[-1]}.py")


def _is_generated(path: Path) -> bool:
    return path.is_relative_to(CLIENTS_DIR) and not path.is_relative_to(METAPACKAGE_DIR)


def _soften(finding: Finding) -> Finding:
    """Codegen owns generated clients, and no aio naming finding crashes at runtime."""
    if finding.severity == "error" and _is_generated(finding.path):
        return replace(finding, severity="warning")
    return finding


if __name__ == "__main__":
    sys.exit(main())
