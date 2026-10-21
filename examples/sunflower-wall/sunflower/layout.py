"""Pure math (no CAD): petal angles, seed positions, petal shape functions."""
import math
from dataclasses import dataclass

import numpy as np
from scipy.spatial import Voronoi

from sunflower.params import Params, Ring

GOLDEN = math.pi * (3 - math.sqrt(5))


def back_angles(p: Params) -> list[float]:
    return [k * p.pitch for k in range(p.petals)]


def front_angles(p: Params) -> list[float]:
    """Front petals sit over the back ring's gaps."""
    return [(k + 0.5) * p.pitch for k in range(p.petals)]


def half_width(ring: Ring, r: float) -> float:
    """Petal half width at radius r: zero at both ends, widest a little past the middle, pointed tip."""
    s = (r - ring.r0) / (ring.r1 - ring.r0)
    if s <= 0 or s >= 1:
        return 0.0
    return ring.width / 2 * math.sin(math.pi * s) ** 0.6


def petal_top(p: Params, ring: Ring, r: float, y: float, hw: float, veins: bool = True) -> float:
    """Petal top at radius r, y across from the midrib (hw = half width there): the midrib height, falling by
    `drop` toward the edges (or down to the ring's `edge` heights, never below petal_min), with `petal_veins`
    lengthwise grooves `vein_depth` deep. Veins follow the petal's width, so they gather toward the root and the tip
    like real ones."""
    u = y / hw
    mid = midrib(ring, r)
    drop = ring.drop if ring.edge is None else max(mid - max(_through(ring.edge, r), p.petal_min), 0.0)
    z = mid - drop * min(u * u, 1.5)
    if veins and abs(u) <= 1:
        z -= p.vein_depth * (1 - math.cos(math.pi * p.petal_veins * (u + 1))) / 2
    return z


def valley_u(p: Params, k: int) -> float:
    """Valley k's place across the petal, as a fraction of the half width (-1 to 1); the midrib is the middle one."""
    return (2 * k + 1) / p.petal_veins - 1


def bead_width(p: Params, r: float) -> float:
    """Orange bead width at radius r: one line at the start, widening over bead_fade, then tapering back to one
    line at the end; 0 outside the bead."""
    r0, r1 = p.bead_r
    if r < r0 or r > r1:
        return 0.0
    if r < r0 + p.bead_fade:
        return p.bead_w_end + (p.bead_w - p.bead_w_end) * (r - r0) / p.bead_fade
    return p.bead_w - (p.bead_w - p.bead_w_end) * (r - r0 - p.bead_fade) / (r1 - r0 - p.bead_fade)


def midrib(ring: Ring, r: float) -> float:
    """Top of the petal along its midrib: smoothstep through the profile points."""
    return _through(ring.profile, r)


def _through(pts: tuple, r: float) -> float:
    """Smoothstep through (r, z) points; flat beyond the ends."""
    if r <= pts[0][0]:
        return pts[0][1]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if r <= r1:
            t = (r - r0) / (r1 - r0)
            return z0 + (z1 - z0) * t * t * (3 - 2 * t)
    return pts[-1][1]


def _cross(u, v) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _shrink(poly: np.ndarray, d: float) -> np.ndarray:
    """Convex counter-clockwise polygon with every edge moved inward by d."""
    n = len(poly)
    lines = []
    for k in range(n):
        t = poly[(k + 1) % n] - poly[k]
        t = t / np.linalg.norm(t)
        lines.append((poly[k] + np.array([-t[1], t[0]]) * d, t))
    out = []
    for k in range(n):
        (p1, t1), (p2, t2) = lines[k - 1], lines[k]
        out.append(p1 + t1 * _cross(p2 - p1, t2) / _cross(t1, t2))
    return np.array(out)


def _clip_circle(poly: np.ndarray, radius: float, sides: int = 180) -> np.ndarray:
    """Sutherland-Hodgman clip of a convex polygon to a circle (as a fine polygon)."""
    out = poly
    for k in range(sides):
        a0, a1 = 2 * math.pi * k / sides, 2 * math.pi * (k + 1) / sides
        A = radius * np.array([math.cos(a0), math.sin(a0)])
        B = radius * np.array([math.cos(a1), math.sin(a1)])
        inside = lambda q: _cross(B - A, q - A) >= 0
        cut = lambda q0, q1: q0 + (q1 - q0) * _cross(A - q0, B - A) / _cross(q1 - q0, B - A)
        new = []
        for j in range(len(out)):
            cur, prv = out[j], out[j - 1]
            if inside(cur):
                if not inside(prv):
                    new.append(cut(prv, cur))
                new.append(cur)
            elif inside(prv):
                new.append(cut(prv, cur))
        out = np.array(new)
        if len(out) < 3:
            return out
    return out


def inradius(poly: np.ndarray) -> float:
    """Distance from a convex polygon's vertex centroid to its nearest edge."""
    c = poly.mean(0)
    n = len(poly)
    return min(abs(_cross(poly[(k + 1) % n] - poly[k], c - poly[k])) / np.linalg.norm(poly[(k + 1) % n] - poly[k])
               for k in range(n))


@dataclass(frozen=True)
class Seed:
    cell: tuple  # base polygon (counter-clockwise) on the head's top
    shoulder: float  # straight sides up to here (above the head's top)
    top: float  # pyramid apex plateau
    top_scale: float  # plateau size as a fraction of the base


def seeds(p: Params) -> list[Seed]:
    """Seeds sit at Vogel's spiral points (seed i at r = c * sqrt(i), angle i * golden angle); each takes its
    Voronoi cell (the space nearer to it than to any other), so neighbours along the spirals meet in diamonds.
    Cells shrink by half the gap, narrow across the radius, and stay inside the rim. Each is a column up to its
    shoulder, taller toward the middle (the dome), then a pyramid. Small seeds get a bigger plateau so it prints;
    rim slivers too thin to print are left out."""
    lim = p.center_r - p.seed_edge
    pts, i = [], 0
    while True:  # points past the rim too, so the rim cells are closed
        i += 1
        r = p.seed_c * math.sqrt(i)
        if r > lim + 3 * p.seed_c:
            break
        pts.append((r * math.cos(i * GOLDEN), r * math.sin(i * GOLDEN)))
    pts = np.array(pts)
    vor = Voronoi(pts)
    lay = p.printer.layer
    out = []
    for k, (x, y) in enumerate(pts):
        r = math.hypot(x, y)
        reg = vor.regions[vor.point_region[k]]
        if r > lim or -1 in reg or not reg:
            continue
        cell = vor.vertices[reg]
        c = cell.mean(0)
        cell = cell[np.argsort(np.arctan2(cell[:, 1] - c[1], cell[:, 0] - c[0]))]
        keep = [cell[0]]
        for q in cell[1:]:
            if np.linalg.norm(q - keep[-1]) > p.seed_min_edge:
                keep.append(q)
        if np.linalg.norm(keep[0] - keep[-1]) <= p.seed_min_edge:
            keep.pop()
        if len(keep) < 3:
            continue
        gap = next(g for rr, g in p.seed_gaps if r < rr)
        cell = _shrink(np.array(keep), gap / 2)
        c = cell.mean(0)
        if np.linalg.norm(c) > 1e-6:
            ur = c / np.linalg.norm(c)
            ut = np.array([-ur[1], ur[0]])
            rel = cell - c
            cell = c + np.outer(rel @ ur, ur) + np.outer(rel @ ut, ut) * p.seed_narrow
        cell = _clip_circle(cell, lim)
        if len(cell) < 3:
            continue
        inr = inradius(cell)
        if 2 * inr < 2.5 * p.printer.nozzle:
            continue  # a sliver the rim cut off
        top_scale = min(max(p.seed_top, p.printer.nozzle / inr), 0.8)
        shoulder = round((p.seed_shoulder + p.seed_dome * (1 - (r / lim) ** 2)) / lay) * lay
        out.append(Seed(tuple(map(tuple, cell)), shoulder, shoulder + p.seed_pyramid, top_scale))
    return out
