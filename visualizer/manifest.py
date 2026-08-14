"""Turn analysis into a scene, guided by a manifest when there is one.

The manifest is the artifact that carries judgement: which parts belong
together, what to call them, what they mean in plain language, and where the
loop should sit on the plane. A parser cannot supply any of that. When no
manifest exists the package layout stands in, so the tool still produces
something on a repository it has never seen — but the result is the diagram you
could already have drawn from `tree`, and it says so.
"""

from __future__ import annotations

import os
import re
import tomllib

from . import analyze, model
from .model import Edge, Group, Node, Scene, Section, Stat

MANIFEST_NAMES = ("visualizer.toml", ".visualizer.toml")


def find_manifest(root: str) -> str | None:
    for name in MANIFEST_NAMES:
        path = os.path.join(root, name)
        if os.path.exists(path):
            return path
    return None


def _first_sentence(text: str) -> str:
    text = " ".join(text.split())
    if not text:
        return ""
    match = re.search(r"(?<=[.!?])\s", text)
    return text[: match.start()] if match else text


def _title(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").upper()


def _keys(names: list[str]) -> dict[str, str]:
    """One short key per node, preferring its own initials, never colliding."""
    used: set[str] = set()
    out: dict[str, str] = {}
    for name in names:
        stem = os.path.basename(name)
        stem = stem[:-3] if stem.endswith(".py") else stem
        candidates = [c.upper() for c in stem if c.isalnum()]
        key = next((c for c in candidates if c not in used), None)
        if key is None:
            base = (candidates or ["X"])[0]
            n = 1
            while f"{base}{n}" in used:
                n += 1
            key = f"{base}{n}"
        used.add(key)
        out[name] = key
    return out


# ---------------------------------------------------------------------------
# fallback: the package layout stands in for judgement
# ---------------------------------------------------------------------------


def _fallback(root: str, modules: dict[str, analyze.Module]) -> dict:
    """Synthesize the manifest a human would otherwise have written."""
    keys = _keys(list(modules))
    nodes, groups = [], []
    seen_groups: dict[str, list[str]] = {}

    for mid, module in modules.items():
        head = mid.split("/")[0]
        group = _title(head) if "/" in mid else "AT THE ROOT"
        seen_groups.setdefault(group, []).append(mid)
        symbols = len(module.symbols)
        nodes.append(
            {
                "id": mid,
                "key": keys[mid],
                "name": _title(os.path.basename(mid)[:-3]),
                "group": group,
                "kind": model.PLATES if symbols >= 10 else model.BLOCK,
                "count": symbols,
                "what": _first_sentence(module.doc) or f"{os.path.basename(mid)}, undocumented.",
                "built": f"{module.lines} lines of code, {symbols} top-level definitions.",
            }
        )

    for title, members in seen_groups.items():
        groups.append({"title": title, "nodes": members})

    readme = ""
    for name in ("README.md", "readme.md"):
        path = os.path.join(root, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                readme = fh.read()
            break
    intro = ""
    if readme:
        for para in readme.split("\n\n"):
            para = para.strip()
            if para and not para.startswith(("#", "!", "|", "-")):
                intro = " ".join(para.split())
                break

    return {
        "project": {
            "name": os.path.basename(os.path.abspath(root)),
            "variant": "read from the package layout",
            "eyebrow": os.path.basename(os.path.abspath(root)).upper(),
            "title": "The Map",
            "subtitle": "grouped by directory, because no manifest said otherwise",
        },
        "nodes": nodes,
        "groups": groups,
        "what": [
            {
                "heading": "WHAT THIS IS",
                "body": intro or "No README paragraph was found to quote here.",
            },
            {
                "heading": "HOW TO READ IT",
                "body": (
                    "No manifest was found, so the grouping is [[the directory layout]] "
                    "and the descriptions are the first sentence of each module "
                    "docstring. Write a visualizer.toml to say what the parts actually "
                    "mean and where they belong on the plane."
                ),
            },
        ],
        "built": [],
    }


# ---------------------------------------------------------------------------


def load(root: str, modules: dict[str, analyze.Module], path: str | None) -> dict:
    if path is None:
        return _fallback(root, modules)
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    raw.setdefault("project", {})
    raw.setdefault("nodes", [])
    raw.setdefault("groups", [])
    return raw


def compose(
    root: str,
    modules: dict[str, analyze.Module],
    data: dict,
    trace=None,
) -> Scene:
    """Fold analysis, manifest and trace into the one structure the renderer reads."""
    project = data.get("project", {})
    counts = dict(getattr(trace, "counts", {}) or {})
    traced = bool(counts)
    fan = analyze.fan_in(modules)

    declared = data.get("nodes", [])
    known = {spec["id"] for spec in declared}
    excluded = set(data.get("exclude", []))

    nodes: list[Node] = []
    for spec in declared:
        mid = spec["id"]
        module = modules.get(mid)
        symbols = module.symbols if module else []
        node = Node(
            id=mid,
            key=spec.get("key", "?"),
            name=spec.get("name", _title(os.path.basename(mid))),
            group=spec.get("group", ""),
            parent=spec.get("parent"),
            kind=spec.get("kind", model.BLOCK),
            pos=tuple(spec["pos"]) if "pos" in spec else None,
            size=tuple(spec.get("size", (2, 2))),
            lines=module.lines if module else 0,
            fan_in=fan.get(mid, 0),
            calls=counts.get(mid, 0),
            count=spec.get("count", len(symbols)),
            what=spec.get("what", ""),
            built=spec.get("built", ""),
        )
        node.inside, node.inside_edges = _inside(mid, symbols)
        nodes.append(node)

    _size_by_count(nodes, declared)

    # edges: declared ones win, otherwise every internal call site we found
    edges: list[Edge] = []
    for spec in data.get("edges", []):
        kind = spec.get("kind", model.SOLID)
        if kind == "optional":
            # present but not switched on: dashed until the recorded run
            # actually went through both ends of it
            ran = counts.get(spec["from"], 0) and counts.get(spec["to"], 0)
            kind = model.SOLID if ran else model.DASHED
        edges.append(
            Edge(
                src=spec["from"],
                dst=spec["to"],
                kind=kind,
                weight=spec.get("weight", 1),
                label=spec.get("label", ""),
            )
        )
    if not edges:
        for src, dst, weight in analyze.call_edges(modules):
            if src in known and dst in known and src != dst and src not in excluded:
                edges.append(Edge(src=src, dst=dst, weight=weight))

    groups: list[Group] = []
    for spec in data.get("groups", []):
        members = spec.get("nodes")
        if members is None:
            members = [n.id for n in nodes if n.group == spec["title"]]
        groups.append(Group(title=spec["title"], nodes=[m for m in members if m in known]))
    if not groups:
        groups = [Group(title="THE SYSTEM", nodes=[n.id for n in nodes])]

    hops = _hops(trace, nodes, edges)

    scene = Scene(
        repo=project.get("name", os.path.basename(os.path.abspath(root))),
        variant=project.get("variant", "python"),
        eyebrow=project.get("eyebrow", ""),
        title=project.get("title", "The Map"),
        subtitle=project.get("subtitle", ""),
        height_means="calls recorded" if traced else "lines of code",
        nodes=nodes,
        edges=edges,
        groups=groups,
        what=[Section(s.get("heading", ""), s.get("body", "")) for s in data.get("what", [])],
        built=[Section(s.get("heading", ""), s.get("body", "")) for s in data.get("built", [])],
        hops=hops,
        traced=traced,
    )
    scene.stats = _stats(scene, modules, trace, data)
    return scene


def _size_by_count(nodes: list[Node], declared: list[dict]) -> None:
    """Footprint is the second data channel: how many things a module defines.

    Height already carries how hard a module works. Ground area carries how
    much of it there is. A manifest that states a size keeps it.
    """
    top = max((n.count for n in nodes), default=0)
    for node, spec in zip(nodes, declared):
        if "size" in spec or top <= 0:
            continue
        side = 3 + round((node.count / top) ** 0.5)
        side = max(3, min(4, side))
        node.size = (side, side)


def _inside(module_id: str, symbols: list[analyze.Symbol]) -> tuple[list[Node], list[Edge]]:
    """The map one level down: a module's own top-level definitions.

    Ids are qualified by their module. Bare names collide across a package —
    two modules here both define `read`, and two both define `_inside` — and an
    unqualified id would quietly hand one module's description to the other.
    """
    if not symbols:
        return [], []
    shown = sorted(symbols, key=lambda s: -s.lines)[:12]
    keys = _keys([s.name for s in shown])
    qualified = {s.name: f"{module_id}::{s.name}" for s in shown}
    nodes = [
        Node(
            id=qualified[s.name],
            key=keys[s.name],
            name=_title(s.name),
            kind=model.BLOCK,
            size=(3, 3),
            lines=s.lines,
            count=s.lines,
            what=_first_sentence(s.doc) or f"{s.kind} {s.name}, undocumented.",
            built=f"{s.kind}, {s.lines} lines.",
        )
        for s in shown
    ]
    edges = []
    for s in shown:
        for called in dict.fromkeys(s.calls):
            if called in qualified and called != s.name:
                edges.append(Edge(src=qualified[s.name], dst=qualified[called]))
    return nodes, edges


def _hops(trace, nodes: list[Node], edges: list[Edge]) -> list[tuple[str, str]]:
    """The path the flow walks: the recorded one if we have it, else the graph."""
    known = {n.id for n in nodes}
    if trace is not None and getattr(trace, "hops", None):
        from .tracing import compress

        recorded = [h for h in compress(trace.hops) if h[0] in known and h[1] in known]
        if recorded:
            return recorded
    # untraced: walk the declared edges depth-first from whatever has no caller
    out_edges: dict[str, list[str]] = {}
    for e in edges:
        if e.kind == model.SOLID:
            out_edges.setdefault(e.src, []).append(e.dst)
    targets = {e.dst for e in edges if e.kind == model.SOLID}
    roots = [n.id for n in nodes if n.id not in targets]
    if not roots and nodes:
        roots = [nodes[0].id]
    walk: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def descend(node_id: str, depth: int = 0) -> None:
        if depth > 40:
            return
        for nxt in out_edges.get(node_id, []):
            if (node_id, nxt) in seen:
                continue
            seen.add((node_id, nxt))
            walk.append((node_id, nxt))
            descend(nxt, depth + 1)

    for root_id in roots:
        descend(root_id)
    return walk


def _stats(scene: Scene, modules, trace, data) -> list[Stat]:
    """Counted facts for the top bar. Declared ones first, measured ones after."""
    stats = [Stat(s["label"], str(s["value"])) for s in data.get("stats", [])]
    total_lines = sum(m.lines for m in modules.values())
    stats.append(Stat("MODULES", str(len(scene.nodes))))
    stats.append(Stat("LINES OF CODE", f"{total_lines:,}"))
    stats.append(Stat("CALL PATHS", str(len(scene.edges))))
    if scene.traced:
        events = getattr(trace, "events", 0)
        stats.append(Stat("CALLS RECORDED", f"{events:,}"))
        stats.append(Stat("HOPS IN THE FLOW", str(len(scene.hops))))
    else:
        stats.append(Stat("FLOW", "static · not recorded"))
    stats.append(Stat("HEIGHT MEANS", scene.height_means))
    stats.append(Stat("FOOTPRINT MEANS", "definitions"))
    return stats
