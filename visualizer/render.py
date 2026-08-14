"""Draw the plane.

Line art, two colours, no fills that are not ground. Every stroke here is
single-weight: there is no silhouette/interior distinction, because the
reference has none. The only texture in the system is the hatch on a face, and
its direction is what makes a block read as solid — the two side faces are
hatched along opposite isometric axes, which meets as a chevron at the front
corner where they join.
"""

from __future__ import annotations

import html

from . import layout, model
from .iso import Box, poly, project
from .model import Edge, Node, Scene

HATCH_STEP = 4.4
HATCH_WEIGHT = 0.55
GROUND = "#CDC499"

# How an edge is named where the page has to find it again. Plain
# concatenation would be ambiguous; the page builds the same key the same way.
EDGE_SEP = "|"


def key(src: str, dst: str) -> str:
    return f"{src}{EDGE_SEP}{dst}"

PATTERNS = f"""
<pattern id="hatch-top" width="{HATCH_STEP}" height="{HATCH_STEP}" patternUnits="userSpaceOnUse">
  <rect width="{HATCH_STEP}" height="{HATCH_STEP}" fill="{GROUND}"/>
  <line x1="0" y1="0" x2="0" y2="{HATCH_STEP}" stroke="#000" stroke-width="{HATCH_WEIGHT}"/>
</pattern>
<pattern id="hatch-left" width="{HATCH_STEP}" height="{HATCH_STEP}"
         patternUnits="userSpaceOnUse" patternTransform="rotate(30)">
  <rect width="{HATCH_STEP}" height="{HATCH_STEP}" fill="{GROUND}"/>
  <line x1="0" y1="0" x2="{HATCH_STEP}" y2="0" stroke="#000" stroke-width="{HATCH_WEIGHT}"/>
</pattern>
<pattern id="hatch-right" width="{HATCH_STEP}" height="{HATCH_STEP}"
         patternUnits="userSpaceOnUse" patternTransform="rotate(-30)">
  <rect width="{HATCH_STEP}" height="{HATCH_STEP}" fill="{GROUND}"/>
  <line x1="0" y1="0" x2="{HATCH_STEP}" y2="0" stroke="#000" stroke-width="{HATCH_WEIGHT}"/>
</pattern>
"""


def _face(points, pattern: str) -> str:
    return f'<polygon class="f" points="{poly(points)}" fill="url(#{pattern})"/>'


def _solid(box: Box) -> str:
    return (
        _face(box.right, "hatch-right")
        + _face(box.left, "hatch-left")
        + _face(box.top, "hatch-top")
    )


def _block_body(node: Node, height: float) -> tuple[str, Box]:
    """The extrusion itself, in whichever of the three variants applies."""
    gx, gy = node.pos
    w, d = node.size
    whole = Box(gx, gy, w, d, height)

    if node.kind == model.PLATES:
        # a collection of many like things: thin layers, not one solid
        plates = max(3, min(7, node.count // 2 or 3))
        thickness = height / (plates * 1.9)
        gap = thickness * 0.9
        parts = []
        for i in range(plates):
            z = i * (thickness + gap)
            parts.append(_solid(Box(gx, gy, w, d, thickness, z)))
        top = Box(gx, gy, w, d, thickness, (plates - 1) * (thickness + gap))
        return "".join(parts), top

    if node.kind == model.CLUSTER:
        # parallel instances: a row of narrow blocks sharing one footprint
        count = max(2, min(5, node.count or 3))
        slot = d / count
        bar = slot * 0.62
        parts = []
        for i in range(count):
            parts.append(_solid(Box(gx, gy + i * slot, w, bar, height)))
        return "".join(parts), Box(gx, gy, w, bar, height)

    return _solid(whole), whole


def _ground(x0: float, y0: float, x1: float, y1: float) -> str:
    """The faint grid, visible only where nothing covers it."""
    lines = []
    for gx in range(int(x0), int(x1) + 1, 2):
        a, b = project(gx, y0), project(gx, y1)
        lines.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    for gy in range(int(y0), int(y1) + 1, 2):
        a, b = project(x0, gy), project(x1, gy)
        lines.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    return f'<g class="ground">{"".join(lines)}</g>'


def _diamond(x: float, y: float, r: float = 4.0, cls: str = "marker") -> str:
    points = poly([(x, y - r), (x + r, y), (x, y + r), (x - r, y)])
    return f'<polygon class="{cls}" points="{points}"/>'


def level(nodes: list[Node], edges: list[Edge], name: str) -> dict:
    """One map: the SVG for it, plus the screen-space paths the flow walks."""
    scene = Scene(
        repo="", variant="", eyebrow="", title="", subtitle="", height_means="",
        nodes=nodes, edges=edges,
    )
    layout.place(scene)
    heights = layout.assign_heights(nodes)
    paths = layout.route(scene)
    x0, y0, x1, y1 = layout.extent(scene)

    # painter's algorithm: everything sorted by how near the viewer it is.
    # Edge segments sit a hair behind blocks at equal depth, so a line runs
    # under a block rather than across its face.
    items: list[tuple[float, str]] = []

    seen: list[tuple[float, float]] = []  # every screen point the map draws on
    screen_paths: dict[str, list[list[float]]] = {}
    for edge in edges:
        path = paths.get((edge.src, edge.dst))
        if not path:
            continue
        dashed = edge.kind == model.DASHED
        screen = [list(project(gx, gy)) for gx, gy in path]
        screen_paths[key(edge.src, edge.dst)] = screen
        seen.extend((p[0], p[1]) for p in screen)
        run = 0.0  # screen distance so far, so the dashes carry across pieces
        for i in range(len(path) - 1):
            # cut each run into short pieces and sort them individually: a
            # piece standing on ground a block covers has to sort behind that
            # block, and the endpoints of the whole run say nothing about that
            (agx, agy), (bgx, bgy) = path[i], path[i + 1]
            steps = max(1, int(round(abs(bgx - agx) + abs(bgy - agy))))
            for s in range(steps):
                t0, t1 = s / steps, (s + 1) / steps
                p0 = (agx + (bgx - agx) * t0, agy + (bgy - agy) * t0)
                p1 = (agx + (bgx - agx) * t1, agy + (bgy - agy) * t1)
                a, b = project(*p0), project(*p1)
                dash = f' stroke-dasharray="5 4" stroke-dashoffset="{run % 9:.1f}"' if dashed else ""
                run += ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
                items.append((
                    max(p0[0] + p0[1], p1[0] + p1[1]) - 0.01,
                    f'<line class="link" x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
                    f'x2="{b[0]:.1f}" y2="{b[1]:.1f}"{dash}/>',
                ))
        # a resting flow marker, one per path, at its midpoint
        if edge.kind == model.SOLID and len(path) >= 2:
            mgx = sum(p[0] for p in path) / len(path)
            mgy = sum(p[1] for p in path) / len(path)
            mid = min(
                range(len(path) - 1),
                key=lambda i: abs((path[i][0] + path[i][1]) / 2 - (mgx + mgy) / 2),
            )
            (agx, agy), (bgx, bgy) = path[mid], path[mid + 1]
            cx, cy = (agx + bgx) / 2, (agy + bgy) / 2
            sx, sy = project(cx, cy)
            items.append((max(agx + agy, bgx + bgy) - 0.005, _diamond(sx, sy)))

    for node in nodes:
        body, cap = _block_body(node, heights[node.id])
        label_x, label_y = cap.top_centre
        solid = Box(node.pos[0], node.pos[1], node.size[0], node.size[1], heights[node.id])
        seen.extend(solid.silhouette)
        items.append((
            solid.depth,
            f'<g class="block" data-id="{html.escape(node.id, quote=True)}">'
            f"{body}"
            f'<text class="key" x="{label_x:.1f}" y="{label_y + 4:.1f}">'
            f"{html.escape(node.key)}</text>"
            f'<polygon class="hit" points="{poly(solid.silhouette)}"/>'
            "</g>",
        ))

    items.sort(key=lambda item: item[0])
    body = "".join(fragment for _, fragment in items)

    # frame what is actually drawn, not the ground rhombus that surrounds it —
    # an isometric plane large enough to hold the grid leaves the map small
    pad = 26
    minx = min(p[0] for p in seen) - pad
    maxx = max(p[0] for p in seen) + pad
    miny = min(p[1] for p in seen) - pad
    maxy = max(p[1] for p in seen) + pad

    svg = (
        f'<g class="level" data-level="{html.escape(name, quote=True)}">'
        # the ground runs well past the map so its own edge never becomes a
        # line on the canvas — a boundary there would encode nothing
        f"{_ground(x0 - 10, y0 - 10, x1 + 10, y1 + 10)}{body}"
        f'<g class="flow"></g></g>'
    )
    return {
        "svg": svg,
        "box": [minx, miny, maxx - minx, maxy - miny],
        "paths": screen_paths,
    }


def levels(scene: Scene) -> dict[str, dict]:
    """The root map, and one map per block that opens."""
    out = {"": level(scene.nodes, scene.edges, "")}
    for node in scene.nodes:
        if node.inside:
            out[node.id] = level(node.inside, node.inside_edges, node.id)
    return out
