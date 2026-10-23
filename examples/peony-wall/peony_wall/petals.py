"""Peony petals. Each petal is a grid of points: columns across it (v from -1 to 1), each the petal's side profile
(the lean growing from lean0 at the foot to lean at the rim) swept a little round the flower's axis, ending on a
rounded, scalloped rim. The ruffle pushes the points along the surface's normal,
flat at the foot and full at the rim.

The petal is a mesh: its visible top skin over a fill: per column, the 45-degree envelope down from every point
above, to the bed, under the rim's angle. So nothing faces down past 45 degrees (one petal rests on the next, or on
the bed) and the fill is always under the petal: from the front you only see its top.
"""
import math
from functools import lru_cache

import numpy as np

from cadkit.mesh import Mesh

from peony_wall.layout import Spec
from peony_wall.params import Params

STEPS = 60  # integration steps along each column's side


def grid(p: Params, s: Spec) -> tuple[np.ndarray, np.ndarray]:
    """The petal's top skin along +X, as points [column v][row along the side] (x, y, z), and the unit normals
    pointing to its underside."""
    nrow, ncol = p.grid
    pts = np.zeros((ncol, nrow, 3))
    for j in range(ncol):
        v = -1 + 2 * j / (ncol - 1)
        # the rim: an ellipse tangent at the sides (rounded corners), scalloped
        smax = 0.45 + 0.55 * math.sqrt(max(1 - v * v, 0)) ** 0.8
        smax -= p.scallop * (0.5 + 0.5 * math.cos(math.pi * s.waves * v + s.phase))
        xs, zs, ans = [0.0], [0.0], [math.radians(s.lean0)]
        for k in range(1, STEPS + 1):
            a = math.radians(s.lean0 + (s.lean - s.lean0) * (k / STEPS * smax) ** s.bend)
            xs.append(xs[-1] + math.sin(a) * s.length * smax / STEPS)
            zs.append(zs[-1] + math.cos(a) * s.length * smax / STEPS)
            ans.append(a)
        for i in range(nrow):
            k = round(i / (nrow - 1) * STEPS)
            t, a = k / STEPS * smax, ans[k]
            phi = v * math.radians(s.half) * (p.claw + (1 - p.claw) * min(t / 0.4, 1) ** 0.7)  # narrower at the foot
            d = s.amp * math.sin(math.pi * s.waves * v + s.phase) * t ** 2 + s.cup * (1 - v * v) * t
            r, z = s.foot + xs[k] + d * math.cos(a), zs[k] - d * math.sin(a)
            pts[j, i] = (r * math.cos(phi), r * math.sin(phi), z)
    n = np.cross(np.gradient(pts, axis=1), np.gradient(pts, axis=0))
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    if np.dot(n[ncol // 2, 0, :2], pts[ncol // 2, 0, :2]) < 0:  # away from the axis at the foot: the underside
        n = -n
    return pts, n


def fill(p: Params, pts: np.ndarray, n: np.ndarray) -> np.ndarray:
    """The underside, rows lined up with the top skin's: row 0 on the bed, the last at the rim's outer edge. Each
    column is the wall's outer skin pushed out to the 45-degree envelope from every point above it, straight down
    under the rim's angle (the petal's wide top). Where it's just the wall, it keeps the wall exactly: on a tip
    curling in, that's the face you see, and turning it to the rim's angle showed from the front."""
    out = pts + p.wall * n
    rho = np.hypot(out[..., 0], out[..., 1])
    z = np.maximum(out[..., 2], 0.0)
    z[:, 0] = 0.0
    reach = np.array([[max(rho[j, i], (rho[j, i:] - (z[j, i:] - z[j, i]) * p.slope).max())
                       for i in range(pts.shape[1])] for j in range(pts.shape[0])])
    # where it's just the wall (no fill), keep the wall exactly: on a tip curling in, that's the face you see
    own = np.arctan2(out[..., 1], out[..., 0])
    w = np.clip((reach - rho) / 2.0, 0, 1)  # blend to the rim's angle over 2 mm of fill
    ang = own + (own[:, -1:] - own) * w
    q = np.stack([reach * np.cos(ang), reach * np.sin(ang), z], axis=2)
    q = np.where((reach - rho)[..., None] > 1e-9, q, np.concatenate([out[..., :2], z[..., None]], axis=2))
    for j in range(pts.shape[0]):  # rows clamped onto the bed: spread them along it, in from the fill's edge
        flat = np.nonzero(z[j] == 0)[0]
        if len(flat) > 1:
            r0 = np.hypot(*pts[j, 0, :2]) + p.wall
            for k, i in enumerate(flat):
                r = r0 + (reach[j, flat[-1]] - r0) * k / (len(flat) - 1)
                q[j, i, :2] = r * np.cos(ang[j, i]), r * np.sin(ang[j, i])
    return q


@lru_cache
def local(p: Params, s: Spec, fill_under: bool = True) -> Mesh:
    """The petal along +X, unplaced, as a mesh straight from its grids (B-rep skins fitted to them fused into
    invalid pieces): with its fill, or (fill_under=False) just its wall, for comparison."""
    pts, n = grid(p, s)
    under = fill(p, pts, n) if fill_under else pts + p.wall * n
    under[:, 0, 2] = 0.0  # the foot row stands on the bed
    return Mesh.from_grids(pts, under, label=s.kind)


def placed(p: Params, s: Spec, fill_under: bool = True) -> Mesh:
    return local(p, s, fill_under).rotate_z(s.angle)
