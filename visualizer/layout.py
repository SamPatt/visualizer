"""Place blocks on the plane and route the edges between them.

The algorithm gets it roughly right; the manifest pins the rest. That split is
deliberate — a layered layout will never find the legible rectangle a person
draws for a loop, and pretending otherwise would produce a worse map than
letting someone type six coordinates.
"""

from __future__ import annotations

from . import model
from .model import Edge, Node, Scene

GUTTER = 3  # grid units of clear ground between footprints
MIN_HEIGHT = 1.7
MAX_HEIGHT = 6.0


def assign_heights(nodes: list[Node]) -> dict[str, float]:
    """Extrusion height, from whatever the height channel currently means.

    Square-rooted: a module called a thousand times is not a tower a thousand
    units tall, it is a tall block, and the ranking is what has to survive.
    """
    values = [max(n.height_source, 0) for n in nodes]
    top = max(values) if values else 0
    if top <= 0:
        return {n.id: MIN_HEIGHT for n in nodes}
    span = MAX_HEIGHT - MIN_HEIGHT
    heights = {}
    for node, value in zip(nodes, values):
        raw = MIN_HEIGHT + span * (value / top) ** 0.5
        # nothing rises much past its own footprint: a tower reads as a
        # different kind of object, not as a taller one
        heights[node.id] = min(raw, 1.25 * min(node.size))
    return heights


def _layers(nodes: list[Node], edges: list[Edge]) -> dict[str, int]:
    """Longest-path layering over solid edges, cycle-safe."""
    ids = [n.id for n in nodes]
    incoming = {i: [] for i in ids}
    for e in edges:
        if e.kind == model.SOLID and e.src in incoming and e.dst in incoming:
            incoming[e.dst].append(e.src)
    layer = {i: 0 for i in ids}
    for _ in range(len(ids)):
        changed = False
        for node_id in ids:
            for src in incoming[node_id]:
                if layer[src] + 1 > layer[node_id]:
                    layer[node_id] = layer[src] + 1
                    changed = True
        if not changed:
            break
    return layer


def place(scene: Scene) -> None:
    """Give every node a grid position. Manifest positions are left alone."""
    unplaced = [n for n in scene.nodes if n.pos is None]
    if not unplaced:
        return

    layer = _layers(unplaced, scene.edges)
    by_layer: dict[int, list[Node]] = {}
    for node in unplaced:
        by_layer.setdefault(layer[node.id], []).append(node)

    taken = [
        (n.pos[0], n.pos[1], n.size[0], n.size[1])
        for n in scene.nodes
        if n.pos is not None
    ]
    gx = max((x + w + GUTTER for x, _, w, _ in taken), default=0)

    for index in sorted(by_layer):
        column = by_layer[index]
        gy = 0
        for node in column:
            node.pos = (gx, gy)
            gy += node.size[1] + GUTTER
        gx += max(n.size[0] for n in column) + GUTTER


# ---------------------------------------------------------------------------
# edges
# ---------------------------------------------------------------------------


def _rect(node: Node) -> tuple[float, float, float, float]:
    x, y = node.pos
    w, d = node.size
    return x, y, x + w, y + d


def _centre(node: Node) -> tuple[float, float]:
    x0, y0, x1, y1 = _rect(node)
    return (x0 + x1) / 2, (y0 + y1) / 2


def _inside(point: tuple[float, float], rect: tuple[float, float, float, float]) -> bool:
    x, y = point
    x0, y0, x1, y1 = rect
    return x0 <= x <= x1 and y0 <= y <= y1


def _search(
    start: tuple[int, int],
    goal: tuple[int, int],
    blocked: set[tuple[int, int]],
    bounds: tuple[int, int, int, int],
) -> list[tuple[int, int]] | None:
    """Shortest orthogonal route around the footprints, turns charged for.

    Two candidate elbows are not enough: with anything in the way they send a
    line swinging out across empty ground, which reads as a relationship that
    is not there. Charging for turns keeps the result to long straight runs in
    the channels between blocks, which is what a person drawing this would do.
    """
    import heapq

    x0, y0, x1, y1 = bounds
    turn_cost = 3
    start_state = (start, (0, 0))
    frontier = [(0, 0, start_state)]
    best = {start_state: 0}
    came: dict = {start_state: None}
    tie = 0

    def heuristic(cell):
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    while frontier:
        _, _, state = heapq.heappop(frontier)
        cell, heading = state
        if cell == goal:
            path = []
            while state is not None:
                path.append(state[0])
                state = came[state]
            return path[::-1]
        for step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cell[0] + step[0], cell[1] + step[1])
            if not (x0 <= nxt[0] <= x1 and y0 <= nxt[1] <= y1):
                continue
            if nxt in blocked and nxt != goal:
                continue
            cost = best[state] + 1 + (turn_cost if heading not in (step, (0, 0)) else 0)
            nxt_state = (nxt, step)
            if cost < best.get(nxt_state, 1 << 30):
                best[nxt_state] = cost
                came[nxt_state] = state
                tie += 1
                heapq.heappush(frontier, (cost + heuristic(nxt), tie, nxt_state))
    return None


def _simplify(cells: list[tuple[int, int]]) -> list[tuple[float, float]]:
    """Keep only the corners; a run of collinear cells is one segment."""
    out: list[tuple[float, float]] = [tuple(map(float, cells[0]))]
    for i in range(1, len(cells) - 1):
        ax, ay = cells[i - 1]
        bx, by = cells[i]
        cx, cy = cells[i + 1]
        if (bx - ax, by - ay) != (cx - bx, cy - by):
            out.append((float(bx), float(by)))
    out.append(tuple(map(float, cells[-1])))
    return out


def _trim(path: list[tuple[float, float]], rect, from_start: bool) -> list[tuple[float, float]]:
    """Cut the path back to where it leaves a footprint, so lines meet block sides."""
    pts = path if from_start else path[::-1]
    out = list(pts)
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        steps = max(int((abs(bx - ax) + abs(by - ay)) * 8), 1)
        for s in range(steps + 1):
            t = s / steps
            point = (ax + (bx - ax) * t, ay + (by - ay) * t)
            if not _inside(point, rect):
                out = [point, *pts[i + 1 :]]
                return out if from_start else out[::-1]
    return path


def route(scene: Scene) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """An orthogonal grid-space polyline per edge, routed around the blocks."""
    by_id = {n.id: n for n in scene.nodes if n.pos is not None}
    x0, y0, x1, y1 = (int(v) for v in extent(scene))
    bounds = (x0, y0, x1, y1)

    cells: dict[str, set[tuple[int, int]]] = {}
    for node in by_id.values():
        px, py = node.pos
        w, d = node.size
        cells[node.id] = {
            (gx, gy) for gx in range(px, px + w + 1) for gy in range(py, py + d + 1)
        }
    everything = set().union(*cells.values()) if cells else set()

    paths: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for edge in scene.edges:
        a, b = by_id.get(edge.src), by_id.get(edge.dst)
        if a is None or b is None or a is b:
            continue
        blocked = everything - cells[a.id] - cells[b.id]
        start = tuple(int(round(v)) for v in _centre(a))
        goal = tuple(int(round(v)) for v in _centre(b))
        found = _search(start, goal, blocked, bounds)
        if found is None:  # boxed in: fall back to a straight elbow
            (ax, ay), (bx, by) = _centre(a), _centre(b)
            path = [(ax, ay), (bx, ay), (bx, by)]
        else:
            path = _simplify(found)
        path = [p for i, p in enumerate(path) if i == 0 or p != path[i - 1]]
        path = _trim(path, _rect(a), True)
        path = _trim(path, _rect(b), False)
        paths[(edge.src, edge.dst)] = path

    return paths


def extent(scene: Scene) -> tuple[float, float, float, float]:
    """The grid rectangle the whole map occupies, with a margin of clear ground."""
    xs, ys = [], []
    for node in scene.nodes:
        if node.pos is None:
            continue
        x0, y0, x1, y1 = _rect(node)
        xs += [x0, x1]
        ys += [y0, y1]
    if not xs:
        return 0, 0, 10, 10
    return min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2
