"""The scene the renderer draws.

Everything upstream — the static reader, the tracer, the manifest — ends up as
one `Scene`. Nothing else in the program knows where a number came from, which
is what lets a traced run and an untraced one share a renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


BLOCK = "block"  # one solid extrusion
PLATES = "plates"  # several thin layers: a collection of many like things
CLUSTER = "cluster"  # a row of narrow blocks: parallel instances

SOLID = "solid"
DASHED = "dashed"


@dataclass
class Node:
    """One block on the plane."""

    id: str
    key: str  # the short key that appears on the block and in the sidebar
    name: str
    group: str = ""
    parent: str | None = None  # sidebar nesting, not containment
    kind: str = BLOCK

    # footprint and placement, in grid units
    pos: tuple[int, int] | None = None  # set by layout when the manifest is silent
    size: tuple[int, int] = (2, 2)

    # measured facts
    lines: int = 0
    fan_in: int = 0
    calls: int = 0  # recorded, 0 when untraced
    count: int = 0  # what the sidebar shows on the right

    # words
    what: str = ""
    built: str = ""

    # the map one level down, if this block opens
    inside: list[Node] = field(default_factory=list)
    inside_edges: list[Edge] = field(default_factory=list)

    @property
    def height_source(self) -> int:
        return self.calls or self.lines


@dataclass
class Edge:
    src: str
    dst: str
    kind: str = SOLID
    weight: int = 1
    label: str = ""


@dataclass
class Group:
    title: str
    nodes: list[str] = field(default_factory=list)


@dataclass
class Stat:
    label: str
    value: str


@dataclass
class Section:
    heading: str
    body: str  # [[double brackets]] mark an inverted inline highlight


@dataclass
class Scene:
    repo: str
    variant: str
    eyebrow: str
    title: str
    subtitle: str
    height_means: str

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    stats: list[Stat] = field(default_factory=list)
    what: list[Section] = field(default_factory=list)
    built: list[Section] = field(default_factory=list)
    hops: list[tuple[str, str]] = field(default_factory=list)
    traced: bool = False

    def node(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None
