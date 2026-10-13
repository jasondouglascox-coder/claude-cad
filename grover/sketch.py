"""Hand-traced Grover (art/cat_sketch.dxf, an Onshape sketch) -> shapely geometry in keychain mm.

The sketch's two circles are the badge ring; scaling its outer circle onto the traced ring
puts every line in the same frame as the rest of the design (origin = ring center).

    head     open outline (sides + ears), ends where Grover goes behind the ribbon
    paws     closed loops resting over the ribbon
    eyes     [(x, y, r)] circles fitted to each eye's closed shapes
    glints   [(x, y, r)] small closed loops inside the eyes
    nose     filled polygon
    lines    every sketch line (drawn as brown strokes where they fall inside Grover)
"""

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import ezdxf
import numpy as np
import shapely
from shapely.affinity import scale, translate
from shapely.geometry import LineString, MultiLineString, Polygon
from shapely.ops import linemerge, polygonize, unary_union

SKETCH = Path(__file__).resolve().parent.parent / "art" / "cat_sketch.dxf"


@dataclass
class Sketch:
    head: Polygon  # whole silhouette incl. the part hidden behind the ribbon
    paws: list
    eyes: list
    glints: list
    nose: Polygon
    lines: MultiLineString


def chaikin(coords, iters: int = 3, sharp_deg: float = 50.0, closed: bool = False):
    """Corner-cutting smoothing that keeps sharp corners (ear tips, paw corners) sharp."""
    pts = [tuple(c) for c in coords]
    if closed and pts[0] == pts[-1]:
        pts = pts[:-1]
    for _ in range(iters):
        n = len(pts)
        out = []
        rng = range(n) if closed else range(n - 1)
        if not closed:
            out.append(pts[0])
        for i in rng:
            a, b = np.array(pts[i]), np.array(pts[(i + 1) % n])
            out += [tuple(0.75 * a + 0.25 * b), tuple(0.25 * a + 0.75 * b)]
            j = (i + 1) % n
            if (closed or j < n - 1) and _turn(pts[i], pts[j], pts[(j + 1) % n]) > sharp_deg:
                out.insert(len(out) - 1, pts[j])  # keep the corner vertex itself
        if not closed:
            out.append(pts[-1])
        pts = out
    return pts + ([pts[0]] if closed else [])


def _turn(a, b, c) -> float:
    v1, v2 = np.subtract(b, a), np.subtract(c, b)
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    return math.degrees(math.acos(np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)))


def fit_circle(pts: np.ndarray):
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    (cx, cy, c), *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    return float(cx), float(cy), math.sqrt(c + cx * cx + cy * cy)


@lru_cache(maxsize=4)
def load(r_out_mm: float, path: str = str(SKETCH)) -> Sketch:
    msp = ezdxf.readfile(path).modelspace()
    raw, circles = [], []
    for e in msp:
        if e.dxftype() == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                pts.append(pts[0])
            raw.append(LineString(pts))
        elif e.dxftype() == "CIRCLE":
            circles.append((e.dxf.center.x, e.dxf.center.y, e.dxf.radius))
    cx, cy, r_big = max(circles, key=lambda c: c[2])
    s = r_out_mm / r_big

    def T(g):
        return scale(translate(g, -cx, -cy), s, s, origin=(0, 0))

    # snap to a 1 micron grid: Onshape's shared endpoints differ in the last digits
    merged = linemerge(unary_union([shapely.set_precision(T(g), 1e-3) for g in raw]))
    parts = list(getattr(merged, "geoms", [merged]))
    closed = [g for g in parts if g.is_ring]
    opened = [g for g in parts if not g.is_ring]

    # The outline is open at the bottom (behind the ribbon). Its two ends are the lowest
    # junctions where three lines meet (side of head + paw top + paw side); close it below them.
    from collections import Counter

    deg = Counter(q for g in opened for q in (g.coords[0], g.coords[-1]))
    nodes = sorted((q for q, n in deg.items() if n >= 3), key=lambda q: q[1])[:2]
    (ax, ay), (bx, by) = sorted(nodes)
    y_low = min(g.bounds[1] for g in parts) - 1.0
    closing = LineString([(ax, ay), (ax, y_low), (bx, y_low), (bx, by)])
    head = unary_union(list(polygonize(unary_union(parts + [closing]))))
    head = Polygon(max(getattr(head, "geoms", [head]), key=lambda g: g.area).exterior)
    head = Polygon(chaikin(head.exterior.coords, closed=True)).buffer(0)

    faces = list(polygonize(parts))  # areas in mm^2
    paws = sorted([f for f in faces if f.area > 15.0], key=lambda f: f.centroid.x)
    small = [f for f in faces if f.area <= 15.0]
    nose = min((f for f in small if f.area > 1.5), key=lambda f: f.centroid.y)  # lowest mid-size shape
    eye_parts = [f for f in small if f.area > 0.35 and not f.equals(nose)]
    eyes = []
    for side in (-1, 1):
        grp = [f for f in eye_parts if (f.centroid.x - nose.centroid.x) * side > 0]
        eyes.append(fit_circle(np.array(unary_union(grp).convex_hull.exterior.coords)))
    eyes.sort()
    glints = []
    for f in small:
        if f.area <= 0.6:
            gx, gy = f.centroid.x, f.centroid.y
            for ex, ey, er in eyes:
                if math.hypot(gx - ex, gy - ey) < er - 0.5:
                    glints.append((gx, gy, math.sqrt(f.area / math.pi)))
    nose = Polygon(chaikin(nose.exterior.coords, closed=True))
    paws = [Polygon(chaikin(p.exterior.coords, closed=True)) for p in paws]
    # interior lines only: the silhouette gets its own generated outline
    def on_outline(g):
        pts = np.array(g.segmentize(0.2).coords)
        near = [head.exterior.distance(shapely.Point(q)) < 0.1 for q in pts]
        return np.mean(near) > 0.6

    lines = MultiLineString([LineString(chaikin(g.coords)) for g in opened if not on_outline(g)] +
                            [LineString(chaikin(g.coords, closed=True)) for g in closed])
    return Sketch(head=head, paws=paws, eyes=eyes, glints=glints, nose=nose, lines=lines)
