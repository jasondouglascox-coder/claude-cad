"""Lily tepals. Each is a grid of points: rows along its midrib, which rises straight out of the throat, is level
`level` of the way along and recurves down until the tip lands on the bed; columns across it, narrow at the foot,
widest past the middle, closing to a fine point, the edges curling down from the midrib, the margins rippled. A
mesh straight from the grid (top skin, a wall's thickness under it): fused B-rep freeform petals came out invalid
on the peony.
"""
import math
from functools import lru_cache

import numpy as np

from cadkit.mesh import Mesh
from lily_wall.params import Params


def angle(p: Params, k: int) -> float:
    """Where tepal k points (deg): one straight up (+Y), the rest every 60 degrees."""
    return 90.0 + k * 360.0 / p.tepals


def _grid(p: Params, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Tepal k along +X: top-skin points [column][row] and each row's normal (to the side you see)."""
    i = k % 2  # 0 outer (a sepal), 1 inner
    rows, cols = p.grid
    t = np.linspace(0, 1, rows)
    lean = np.where(t < p.level, 90 * t / p.level, 90 + (p.lean_tip[i] - 90) * (t - p.level) / (1 - p.level))
    a = np.radians(lean)
    ds = p.length[i] / (rows - 1)
    x = p.foot[i] + np.concatenate([[0], np.cumsum(np.sin(a[:-1]) * ds)])
    z = np.concatenate([[0], np.cumsum(np.cos(a[:-1]) * ds)])
    n = np.stack([-np.cos(a), np.zeros_like(a), np.sin(a)], 1)  # up and in: the face you see
    half = p.width[i] / 2 * (0.12 + 0.88 * np.sin(np.pi * t ** 0.75) ** 0.9) * (1 - t ** p.point)
    pts = np.zeros((cols, rows, 3))
    for j, v in enumerate(np.linspace(-1, 1, cols)):
        drop = p.convex * half * v * v + p.ripple * abs(v) ** 3 * np.sin(2 * np.pi * p.ripples * t + 3 * v) * t
        pts[j] = np.stack([x, half * v, z], 1) - drop[:, None] * n
    return pts, n


def grid(p: Params, k: int) -> np.ndarray:
    return _grid(p, k)[0]


def placed_grid(p: Params, k: int) -> np.ndarray:
    c, s = math.cos(math.radians(angle(p, k))), math.sin(math.radians(angle(p, k)))
    return grid(p, k) @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])


@lru_cache
def local(p: Params, k: int) -> Mesh:
    pts, n = _grid(p, k)
    under = pts - p.wall * n[None]
    under[:, 0, 2] = 0.0  # the foot stands on the bed
    under[:, -1, 2] = np.maximum(under[:, -1, 2], 0.0)  # and so does the tip
    under[..., 2] = np.maximum(under[..., 2], 0.0)
    return Mesh.from_grids(pts, under, label="tepal")


def placed(p: Params, k: int) -> Mesh:
    return local(p, k).rotate_z(angle(p, k))
