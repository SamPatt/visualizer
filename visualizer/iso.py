"""True isometric projection, and the geometry of an extruded rectangle.

Grid space is right-handed: +gx recedes to the lower right of the screen, +gy to
the lower left, +gz is up. One grid unit on the ground is `UNIT` pixels wide
along its axis; one unit of height is `RISE` pixels.
"""

from __future__ import annotations

import math

COS30 = math.cos(math.radians(30))
SIN30 = 0.5

UNIT = 34.0
RISE = 26.0


def project(gx: float, gy: float, gz: float = 0.0) -> tuple[float, float]:
    """Grid coordinates to screen coordinates."""
    return (
        (gx - gy) * COS30 * UNIT,
        (gx + gy) * SIN30 * UNIT - gz * RISE,
    )


def poly(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def depth(gx: float, gy: float) -> float:
    """Painter's-algorithm key. Larger is nearer the viewer."""
    return gx + gy


class Box:
    """An axis-aligned box on the grid, with its visible faces.

    Only three faces can face this camera: the top, the face at max gy (which
    reads as the front-left), and the face at max gx (the front-right).
    """

    def __init__(self, gx: float, gy: float, w: float, d: float, h: float, z: float = 0.0):
        self.gx, self.gy, self.w, self.d, self.h, self.z = gx, gy, w, d, h, z

    @property
    def top(self) -> list[tuple[float, float]]:
        x, y, w, d, t = self.gx, self.gy, self.w, self.d, self.z + self.h
        return [
            project(x, y, t),
            project(x + w, y, t),
            project(x + w, y + d, t),
            project(x, y + d, t),
        ]

    @property
    def left(self) -> list[tuple[float, float]]:
        """The face at max gy."""
        x, y, w, d = self.gx, self.gy, self.w, self.d
        top, bot = self.z + self.h, self.z
        return [
            project(x, y + d, top),
            project(x + w, y + d, top),
            project(x + w, y + d, bot),
            project(x, y + d, bot),
        ]

    @property
    def right(self) -> list[tuple[float, float]]:
        """The face at max gx."""
        x, y, w, d = self.gx, self.gy, self.w, self.d
        top, bot = self.z + self.h, self.z
        return [
            project(x + w, y, top),
            project(x + w, y + d, top),
            project(x + w, y + d, bot),
            project(x + w, y, bot),
        ]

    @property
    def silhouette(self) -> list[tuple[float, float]]:
        """The outline of the whole solid — used for hit-testing, not drawing."""
        x, y, w, d = self.gx, self.gy, self.w, self.d
        top, bot = self.z + self.h, self.z
        return [
            project(x, y, top),
            project(x + w, y, top),
            project(x + w, y, bot),
            project(x + w, y + d, bot),
            project(x, y + d, bot),
            project(x, y + d, top),
        ]

    @property
    def top_centre(self) -> tuple[float, float]:
        return project(self.gx + self.w / 2, self.gy + self.d / 2, self.z + self.h)

    @property
    def depth(self) -> float:
        """The near corner, not the far one.

        A box has to sort after anything standing inside its own footprint —
        an edge crossing the ground it covers is behind it, whatever the
        midpoint of that edge works out to.
        """
        return depth(self.gx + self.w, self.gy + self.d)
