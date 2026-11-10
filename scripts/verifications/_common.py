# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Shared package, module and import-graph index for the verification scripts."""

import ast
import functools
import importlib.metadata
import json
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROJECT_GLOBS = ("clients/*/pyproject.toml", "packages/*/pyproject.toml")
PROBE = HERE / "_probe.py"
# Matched with and without suffix, so a generated models.pyi stub counts too.
MODEL_DATA = ("models", "_private/schemas")
AIO = "aio"

type Severity = Literal["error", "warning", "info"]
type Context = Literal["runtime", "type_checking", "deferred"]


@dataclass(frozen=True)
class Finding:
    message: str
    path: Path | None = None
    line: int = 0
    severity: Severity = "error"

    def __str__(self) -> str:
        where = ""
        if self.path is not None:
            where = (
                f"{relative(self.path)}:{self.line}: "
                if self.line
                else f"{relative(self.path)}: "
            )
        return f"{where}{self.severity}: {self.message}"


@dataclass
class Package:
    dir: Path
    pyproject: dict[str, Any]

    @property
    def dist(self) -> str:
        return canonicalize_name(self.pyproject["project"]["name"])

    @property
    def src(self) -> Path:
        return self.dir / "src"

    @property
    def roots(self) -> list[str]:
        return sorted(
            p.name for p in self.src.iterdir() if (p / "__init__.py").exists()
        )

    @property
    def dependencies(self) -> list[Requirement]:
        return [
            Requirement(r) for r in self.pyproject["project"].get("dependencies", [])
        ]

    @property
    def extras(self) -> dict[str, list[Requirement]]:
        optional = self.pyproject["project"].get("optional-dependencies", {})
        return {k: [Requirement(r) for r in v] for k, v in optional.items()}

    @property
    def version_file(self) -> Path | None:
        """The file hatch reads a dynamic version from."""
        path = (
            self.pyproject.get("tool", {})
            .get("hatch", {})
            .get("version", {})
            .get("path")
        )
        return self.dir / path if path else None

    @property
    def source_version(self) -> str | None:
        """The literal ``__version__`` in the version file or package ``__init__``."""
        candidates = [self.version_file] + [
            self.src / r / "__init__.py" for r in self.roots
        ]
        for path in candidates:
            if path is None or not path.exists():
                continue
            for node in ast.parse(path.read_text()).body:
                if (
                    isinstance(node, ast.Assign)
                    and any(
                        isinstance(t, ast.Name) and t.id == "__version__"
                        for t in node.targets
                    )
                    and isinstance(node.value, ast.Constant)
                ):
                    return str(node.value.value)
        return None

    @property
    def current_version(self) -> Version | None:
        project = self.pyproject["project"]
        if "version" in project:
            return Version(project["version"])
        found = self.source_version
        return Version(found) if found else None

    @property
    def extras_only(self) -> set[str]:
        """Distributions declared only under extras."""
        required = {canonicalize_name(r.name) for r in self.dependencies}
        return {
            canonicalize_name(r.name) for reqs in self.extras.values() for r in reqs
        } - required


@dataclass
class Import:
    module: "Module"
    target: str
    name: str | None
    asname: str | None
    line: int
    context: Context
    guarded: bool

    @property
    def top(self) -> str:
        return self.target.split(".")[0]


@dataclass
class Module:
    name: str
    path: Path
    src: Path
    package: Package | None

    @functools.cached_property
    def tree(self) -> ast.Module:
        return ast.parse(self.path.read_bytes(), filename=str(self.path))

    @property
    def is_package(self) -> bool:
        return self.path.stem == "__init__"

    @property
    def public(self) -> bool:
        return not any(p.startswith("_") for p in self.name.split("."))

    @property
    def in_aio(self) -> bool:
        return AIO in self.name.split(".")

    @property
    def model_data(self) -> bool:
        """Whether this is a generated client's per-shape module.

        These hold most of the repo's source and repeat one codegen template per
        shape, so AST analyses skip them; checks that import modules still cover them.
        """
        return self.package is not None and is_model_data(self.package, self.path)

    @functools.cached_property
    def imports(self) -> list[Import]:
        if self.model_data:
            return []
        return list(_ImportCollector(self).collect())

    @functools.cached_property
    def defined(self) -> set[str]:
        """Names bound at module level by def, class, assignment or type alias.

        Includes a sibling stub's bindings: lazily built models exist only there.
        """
        return set(_top_level_bindings(self.tree.body)) | set(self.stub_names)

    @functools.cached_property
    def stub_names(self) -> list[str]:
        """Names bound at module level in the sibling ``.pyi`` stub, in order.

        Lazily built members are in neither ``vars()`` nor ``dir()`` of the
        module, so the stub is the only place that lists them.
        """
        stub = self.path.with_suffix(".pyi")
        if not stub.exists():
            return []
        body = ast.parse(stub.read_bytes(), filename=str(stub)).body
        return list(dict.fromkeys(_top_level_bindings(body)))

    @functools.cached_property
    def imported(self) -> dict[str, Import]:
        """Names bound at module level by an import, keyed by bound name."""
        bound: dict[str, Import] = {}
        for imp in self.imports:
            if imp.context == "deferred":
                continue
            if imp.name is None:
                key = imp.asname or imp.target.split(".")[0]
            else:
                key = imp.asname or imp.name
            bound[key] = imp
        return bound

    @functools.cached_property
    def dunder_all(self) -> list[str] | None:
        for node in self.tree.body:
            targets: list[ast.expr] = []
            value: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                if isinstance(value, ast.List | ast.Tuple):
                    return [
                        e.value
                        for e in value.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)
                    ]
        return None


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


@functools.cache
def packages() -> list[Package]:
    """Every generated client and hand-written package."""
    return [
        Package(p.parent, tomllib.loads(p.read_text()))
        for g in PROJECT_GLOBS
        for p in sorted(ROOT.glob(g))
    ]


@functools.cache
def package_by_dist() -> dict[str, Package]:
    return {p.dist: p for p in packages()}


@functools.cache
def runtime_modules() -> list[Module]:
    found: list[Module] = []
    for package in packages():
        found.extend(_load_src(package.src, package))
    return found


def is_model_data(package: Package, path: Path) -> bool:
    """Whether ``path`` is one of a generated client's per-shape modules or their stubs."""
    if package.dir.parent.name != "clients":
        return False
    rel = path.relative_to(package.src).with_suffix("").as_posix().split("/", 1)[-1]
    return rel in MODEL_DATA


def model_data_globs(package: Package) -> list[str]:
    """Paths of ``package``'s model data for a tool's exclude option."""
    if package.dir.parent.name != "clients":
        return []
    return [
        str(package.src / root / f"{m}.{ext}")
        for root in package.roots
        for m in MODEL_DATA
        for ext in ("py", "pyi")
    ]


def analyzed_modules() -> list[Module]:
    """The modules AST analyses read: every runtime module except model data."""
    return [m for m in runtime_modules() if not m.model_data]


@functools.cache
def module_index() -> dict[str, Module]:
    return {m.name: m for m in runtime_modules()}


@functools.cache
def owned_roots() -> frozenset[str]:
    return frozenset(r for p in packages() for r in p.roots)


@functools.cache
def import_to_dists() -> dict[str, set[str]]:
    """Maps a top-level import name to the distributions that provide it."""
    mapping: dict[str, set[str]] = {
        top: {canonicalize_name(d) for d in dists}
        for top, dists in importlib.metadata.packages_distributions().items()
    }
    # Editable installs don't always report their top-level names.
    for package in packages():
        for root in package.roots:
            mapping.setdefault(root, set()).add(package.dist)
    return mapping


def is_stdlib(top: str) -> bool:
    return top in sys.stdlib_module_names or top == "__future__"


def resolve_from(imp: Import) -> tuple[str, str | None]:
    """The module an import binds and the attribute read from it, if any.

    ``from pkg import sub`` resolves to the submodule when one exists.
    """
    if imp.name is not None:
        sub = f"{imp.target}.{imp.name}"
        if sub in module_index() or sub in native_modules():
            return sub, None
    return imp.target, imp.name


@functools.cache
def native_modules() -> frozenset[str]:
    """Extension modules, which have a stub or shared object but no ``.py`` source."""
    names: set[str] = set()
    for package in packages():
        for path in [*package.src.rglob("*.pyi"), *package.src.rglob("*.so")]:
            if path.with_name(path.name.split(".")[0] + ".py").exists():
                continue
            rel = path.relative_to(package.src)
            names.add(".".join([*rel.parts[:-1], rel.name.split(".")[0]]))
    return frozenset(names)


def canonical_definition(module: str, name: str, depth: int = 0) -> str | None:
    """Follows re-export chains to the module that defines ``name``."""
    found = module_index().get(module)
    if found is None or depth > 16:
        return None
    if name in found.defined:
        return module
    imp = found.imported.get(name)
    if imp is None or imp.name is None:
        return None
    target, attr = resolve_from(imp)
    if attr is None:
        return target
    return canonical_definition(target, attr, depth + 1)


def tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    """Strongly connected components with a cycle: more than one node, or a self-loop."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    result: list[list[str]] = []
    counter = 0

    def strongconnect(v: str) -> None:
        nonlocal counter
        index[v] = low[v] = counter
        counter += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            if len(component) > 1 or v in graph.get(v, ()):
                result.append(sorted(component))

    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10_000))
    for v in sorted(graph):
        if v not in index:
            strongconnect(v)
    return result


def main(title: str, check: Callable[[], list[Finding]]) -> None:
    """Runs one verification, prints its findings, and exits nonzero on any error."""
    findings = check()
    for finding in findings:
        sys.stdout.write(f"{finding}\n")
    sys.stdout.flush()
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    sys.stderr.write(f"{title}: {errors} error(s), {warnings} warning(s).\n")
    sys.exit(1 if errors else 0)


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    timeout: int = 1800,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        args,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def build_wheels(dest: Path) -> list[Path]:
    """Builds a wheel of every package into ``dest``."""

    def one(package: Package) -> None:
        proc = run(["uv", "build", "--wheel", "--out-dir", str(dest), str(package.dir)])
        if proc.returncode != 0:
            raise RuntimeError(
                f"uv build of {package.dist} failed:\n{proc.stderr[-3000:]}"
            )

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        list(pool.map(one, packages()))
    return sorted(dest.glob("*.whl"))


def make_venv(path: Path, *install: str) -> str:
    """Creates a Python 3.12 venv at ``path``, installs ``install`` into it, and returns its python."""
    proc = run(["uv", "venv", "--quiet", "--python", "3.12", str(path)])
    if proc.returncode != 0:
        raise RuntimeError(f"uv venv failed:\n{proc.stderr[-3000:]}")
    python = str(path / "bin" / "python")
    if install:
        proc = run(["uv", "pip", "install", "--python", python, *install])
        if proc.returncode != 0:
            raise RuntimeError(f"uv pip install failed:\n{proc.stderr[-3000:]}")
    return python


def probe(
    modules: Iterable[str], python: str = sys.executable
) -> dict[str, dict[str, Any]]:
    """Imports each module in a fresh interpreter and returns the probe reports."""
    names = list(modules)
    return _probe_cached(tuple(names), python)


def members(module: Module, loaded: ModuleType) -> Iterator[tuple[str, object]]:
    """The loaded module's globals, then the members only its stub names.

    Reading a stub-only name with ``getattr`` builds it through the module's
    ``__getattr__``.
    """
    namespace = vars(loaded)
    yield from list(namespace.items())
    for name in module.stub_names:
        if name not in namespace and hasattr(loaded, name):
            yield name, getattr(loaded, name)


def public_runtime_module_names() -> list[str]:
    return [m.name for m in runtime_modules() if m.public]


def all_runtime_module_names() -> list[str]:
    return [m.name for m in runtime_modules()]


def import_call_aliases(tree: ast.Module) -> set[str]:
    """Local names bound to ``importlib.import_module`` or ``__import__``."""
    names = {"__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name in ("import_module", "__import__"):
                    names.add(alias.asname or alias.name)
    return names


def is_import_call(func: ast.expr, aliases: set[str]) -> bool:
    """Whether ``func`` is ``importlib.import_module``, ``__import__`` or a local alias of them."""
    if isinstance(func, ast.Name):
        return func.id in aliases
    return (
        isinstance(func, ast.Attribute)
        and func.attr in ("import_module", "__import__")
        and isinstance(func.value, ast.Name)
        and func.value.id == "importlib"
    )


@functools.cache
def _probe_cached(names: tuple[str, ...], python: str) -> dict[str, dict[str, Any]]:
    roots = [str(p.src) for p in packages()]

    def one(name: str) -> tuple[str, dict[str, Any]]:
        proc = run([python, str(PROBE), name, *roots], timeout=300)
        try:
            return name, json.loads(proc.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return name, {
                "ok": False,
                "error": {
                    "type": "ProbeCrash",
                    "message": proc.stderr[-2000:],
                    "missing": None,
                },
                "warnings": [],
                "side_effects": [],
            }

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
        return dict(pool.map(one, names))


def _load_src(src: Path, package: Package | None) -> Iterator[Module]:
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src)
        if "__pycache__" in rel.parts:
            continue
        parts = list(rel.parts[:-1])
        if path.stem != "__init__":
            parts.append(path.stem)
        yield Module(name=".".join(parts), path=path, src=src, package=package)


def _top_level_bindings(body: list[ast.stmt]) -> Iterator[str]:
    for node in body:
        match node:
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                yield node.name
            case ast.Assign():
                for target in node.targets:
                    yield from _target_names(target)
            case ast.AnnAssign():
                yield from _target_names(node.target)
            case ast.TypeAlias():
                if isinstance(node.name, ast.Name):
                    yield node.name.id
            case ast.If() | ast.Try():
                yield from _top_level_bindings(node.body)
                yield from _top_level_bindings(node.orelse)
                if isinstance(node, ast.Try):
                    for handler in node.handlers:
                        yield from _top_level_bindings(handler.body)
                    yield from _top_level_bindings(node.finalbody)
            case _:
                pass


def _target_names(target: ast.expr) -> Iterator[str]:
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Tuple | ast.List):
        for elt in target.elts:
            yield from _target_names(elt)


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


_IMPORT_ERRORS = frozenset(
    {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}
)


def _catches_import_error(node: ast.Try) -> bool:
    for handler in node.handlers:
        if handler.type is None:
            return True
        types = (
            handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        )
        for t in types:
            if isinstance(t, ast.Name) and t.id in _IMPORT_ERRORS:
                return True
    return False


class _ImportCollector:
    def __init__(self, module: Module) -> None:
        self.module = module
        self.call_aliases = import_call_aliases(module.tree)

    def collect(self) -> Iterator[Import]:
        yield from self._walk(self.module.tree.body, "runtime", guarded=False)

    def _walk(
        self, body: list[ast.stmt], context: Context, *, guarded: bool
    ) -> Iterator[Import]:
        for node in body:
            yield from self._visit(node, context, guarded=guarded)

    def _visit(
        self, node: ast.AST, context: Context, *, guarded: bool
    ) -> Iterator[Import]:
        match node:
            case ast.Import():
                for alias in node.names:
                    yield Import(
                        self.module,
                        alias.name,
                        None,
                        alias.asname,
                        node.lineno,
                        context,
                        guarded,
                    )
            case ast.Call() if is_import_call(node.func, self.call_aliases):
                if (target := self._call_target(node)) is not None:
                    yield Import(
                        self.module, target, None, None, node.lineno, context, guarded
                    )
                for child in ast.iter_child_nodes(node):
                    yield from self._visit(child, context, guarded=guarded)
            case ast.ImportFrom():
                target = self._absolute(node.level, node.module)
                for alias in node.names:
                    yield Import(
                        self.module,
                        target,
                        alias.name,
                        alias.asname,
                        node.lineno,
                        context,
                        guarded,
                    )
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.Lambda():
                for child in ast.iter_child_nodes(node):
                    yield from self._visit(child, "deferred", guarded=guarded)
            case ast.If() if _is_type_checking(node.test):
                inner: Context = (
                    "deferred" if context == "deferred" else "type_checking"
                )
                yield from self._walk(node.body, inner, guarded=guarded)
                yield from self._walk(node.orelse, context, guarded=guarded)
            case ast.Try():
                catches = _catches_import_error(node)
                yield from self._walk(node.body, context, guarded=guarded or catches)
                for handler in node.handlers:
                    yield from self._walk(handler.body, context, guarded=guarded)
                yield from self._walk(node.orelse, context, guarded=guarded)
                yield from self._walk(node.finalbody, context, guarded=guarded)
            case _:
                for child in ast.iter_child_nodes(node):
                    yield from self._visit(child, context, guarded=guarded)

    def _call_target(self, node: ast.Call) -> str | None:
        """The absolute module a literal ``import_module`` call loads, if statically known."""
        first = node.args[0] if node.args else None
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        name = first.value
        stripped = name.lstrip(".")
        level = len(name) - len(stripped)
        if not level:
            return name
        package = next((k.value for k in node.keywords if k.arg == "package"), None)
        if len(node.args) > 1:
            package = node.args[1]
        # Relative calls resolve against the caller only when anchored to it.
        if not isinstance(package, ast.Name):
            return None
        if package.id == "__package__":
            return self._absolute(level, stripped or None)
        if package.id == "__name__":
            return self._absolute(level, stripped or None, base=self.module.name)
        return None

    def _absolute(self, level: int, module: str | None, base: str | None = None) -> str:
        if not level:
            return module or ""
        if base is not None:
            parts = base.split(".")
        else:
            parts = self.module.name.split(".")
            if not self.module.is_package:
                parts = parts[:-1]
        parts = parts[: len(parts) - (level - 1)]
        if module:
            parts.append(module)
        return ".".join(parts)
