"""Read a Python repository without running it.

This is the structure layer. It answers *what the parts are* and *what could
call what*, which is enough to draw the map. It is deliberately honest about
its own limits: a static edge means "there is a call site here", not "this
call happens".
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist",
    ".mypy_cache", ".pytest_cache", ".tox", "site-packages", ".idea", ".vscode",
}


@dataclass
class Symbol:
    """A top-level function or class: what a block contains when it opens."""

    name: str
    kind: str  # "function" | "class"
    lines: int
    doc: str
    calls: list[str] = field(default_factory=list)  # names called in its body


@dataclass
class Module:
    id: str  # path relative to the repo root, e.g. "visualizer/layout.py"
    dotted: str  # e.g. "visualizer.layout"
    doc: str
    lines: int
    symbols: list[Symbol] = field(default_factory=list)
    # module id -> number of call sites reaching it
    calls: dict[str, int] = field(default_factory=dict)
    imports: dict[str, int] = field(default_factory=dict)


def _code_lines(source: str) -> int:
    """Lines that carry code. Blank lines and whole-line comments do not count."""
    n = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            n += 1
    return n


def _dotted(rel: str) -> str:
    stem = rel[:-3] if rel.endswith(".py") else rel
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem.replace("/", ".")


def find_modules(root: str, exclude: list[str] | None = None) -> list[str]:
    """Every .py file under `root`, as repo-relative paths, sorted."""
    exclude = exclude or []
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            if any(rel.startswith(pattern.rstrip("/")) for pattern in exclude):
                continue
            found.append(rel)
    return sorted(found)


class _Reader(ast.NodeVisitor):
    """Collects imports, call sites and top-level symbols from one module."""

    def __init__(self, module: Module, resolve):
        self.module = module
        self.resolve = resolve
        # local name -> module id it came from
        self.bound: dict[str, str] = {}
        self._symbol: Symbol | None = None

    # -- imports ---------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            target = self.resolve(alias.name, 0, self.module)
            if target:
                self.bound[(alias.asname or alias.name).split(".")[0]] = target
                self.module.imports[target] = self.module.imports.get(target, 0) + 1

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        base = node.module or ""
        for alias in node.names:
            # `from . import layout` names a module, not a member of one; try
            # that reading first or every sibling import collapses onto the
            # package __init__ and the real edges disappear
            joined = f"{base}.{alias.name}" if base else alias.name
            target = self.resolve(joined, node.level, self.module)
            if target is None:
                target = self.resolve(base, node.level, self.module)
            if target is None:
                continue
            self.module.imports[target] = self.module.imports.get(target, 0) + 1
            self.bound[alias.asname or alias.name] = target

    # -- top-level symbols ------------------------------------------------

    def _symbol_def(self, node, kind: str) -> None:
        outer = self._symbol
        if outer is None:  # only top-level definitions become inner blocks
            span = (node.end_lineno or node.lineno) - node.lineno + 1
            self._symbol = Symbol(
                name=node.name,
                kind=kind,
                lines=span,
                doc=(ast.get_docstring(node) or "").strip(),
            )
            self.module.symbols.append(self._symbol)
        self.generic_visit(node)
        if outer is None:
            self._symbol = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._symbol_def(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._symbol_def(node, "function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._symbol_def(node, "class")

    # -- call sites -------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = None
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            name = func.value.id
        if name:
            target = self.bound.get(name)
            if target and target != self.module.id:
                self.module.calls[target] = self.module.calls.get(target, 0) + 1
            if self._symbol is not None:
                self._symbol.calls.append(name)
        self.generic_visit(node)


def read(root: str, exclude: list[str] | None = None) -> dict[str, Module]:
    """Parse every module under `root` and resolve internal calls between them."""
    rels = find_modules(root, exclude)
    modules: dict[str, Module] = {}
    by_dotted: dict[str, str] = {}

    for rel in rels:
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                source = fh.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = Module(
            id=rel,
            dotted=_dotted(rel),
            doc=(ast.get_docstring(tree) or "").strip(),
            lines=_code_lines(source),
        )
        modules[rel] = module
        by_dotted[module.dotted] = rel
        module._tree = tree  # type: ignore[attr-defined]

    def resolve(name: str, level: int, origin: Module) -> str | None:
        """An import target to a module id, or None when it leaves the repo."""
        if level:
            base = origin.dotted.split(".")
            base = base[: len(base) - level] if level <= len(base) else []
            name = ".".join([*base, name]) if name else ".".join(base)
        for candidate in (name, f"{name}.__init__"):
            if candidate in by_dotted:
                return by_dotted[candidate]
        # `from package.module import thing` where `thing` is not a module
        head = name.rsplit(".", 1)[0]
        return by_dotted.get(head)

    for module in modules.values():
        _Reader(module, resolve).visit(module._tree)  # type: ignore[attr-defined]
        del module._tree  # type: ignore[attr-defined]

    return modules


def call_edges(modules: dict[str, Module]) -> list[tuple[str, str, int]]:
    """(source, target, call sites). An import with no call site still counts once."""
    edges: dict[tuple[str, str], int] = {}
    for module in modules.values():
        for target, n in module.calls.items():
            edges[(module.id, target)] = edges.get((module.id, target), 0) + n
        for target in module.imports:
            edges.setdefault((module.id, target), 1)
    return [(src, dst, n) for (src, dst), n in sorted(edges.items())]


def fan_in(modules: dict[str, Module]) -> dict[str, int]:
    counts = {mid: 0 for mid in modules}
    for src, dst, _ in call_edges(modules):
        if dst in counts and src != dst:
            counts[dst] += 1
    return counts
