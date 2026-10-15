"""The ribbon, drawn: v1's hand-traced sketch (art/ribbon_sketch.dxf, an Onshape sketch), registered onto the
logo's own ribbon and moved down with the figure. A front banner and, on each side, a back band with its tail,
slid in toward the middle and carried on until it meets the orange ring (v1's look). Clean lines; the letters stay
traced."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import ezdxf
import numpy as np
import shapely
from shapely.affinity import scale, translate
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

from . import vec as V

SKETCH = Path(__file__).resolve().parent.parent / "art" / "ribbon_sketch.dxf"


@dataclass
class Ribbon:
    front: Polygon  # the banner, outline included
    backs: list  # [left, right] back bands with their tails, outline included
    folds: list  # small folds where the front meets each back band


@lru_cache(maxsize=1)
def raw():
    """(front, [left tail, right tail], folds) in sketch units, each grown by the sketch's outline thickness so it
    includes its outline. The sketch draws both edges of each outline and one tail; the ribbon is symmetric."""
    msp = ezdxf.readfile(SKETCH).modelspace()
    lines = [shapely.set_precision(LineString([(q[0], q[1]) for q in e.get_points("xy")]), 1e-3)
             for e in msp if e.dxftype() == "LWPOLYLINE"]
    faces = sorted(polygonize(unary_union(lines)), key=lambda f: -f.area)
    sil = unary_union(faces)
    front = faces[0]
    cx = front.centroid.x
    top_in = max(y for x, y in front.exterior.coords if abs(x - cx) < 5)
    top_out = max(y for g in getattr(sil, "geoms", [sil]) for x, y in g.exterior.coords if abs(x - cx) < 5)
    t = max(top_out - top_in, 0.0)
    tail_r = max((f for f in faces[1:] if f.centroid.x > cx and f.area > 50), key=lambda f: f.area)
    folds = [f for f in faces if f.area < 0.02 * front.area]
    axis = (min(front.exterior.xy[0]) + max(front.exterior.xy[0])) / 2
    tail_l = scale(tail_r, -1, 1, origin=(axis, 0))

    def grow(g):
        return g.buffer(t, join_style="mitre")

    return grow(front), [grow(tail_l), grow(tail_r)], [grow(f) for f in folds]


def register(target) -> Ribbon:
    """The sketch scaled and shifted onto `target` (the logo's ribbon in mm, outline included)."""
    from scipy.optimize import minimize

    front, tails, folds = raw()
    src = unary_union([front, *tails])
    sb, tb = src.bounds, target.bounds
    s0 = (tb[2] - tb[0]) / (sb[2] - sb[0])
    x0, y0 = tb[0] - sb[0] * s0, tb[3] - sb[3] * s0

    def place(g, v):
        return translate(scale(g, v[0], v[0], origin=(0, 0)), v[1], v[2])

    v = minimize(lambda v: place(src, v).symmetric_difference(target).area, [s0, x0, y0], method="Nelder-Mead",
                 options={"xatol": 1e-4, "fatol": 1e-4, "maxiter": 400}).x
    return Ribbon(place(front, v), [place(t, v) for t in tails], [place(f, v) for f in folds])


def wing(tail: Polygon, side: int, r_ring: float, slide: float) -> Polygon:
    """A tail slid `slide` toward the middle, its straight lower edge carried on until it meets the ring, and the
    band filled up to the ring (v1's wing): no orange shows between the banner, the back band and the ring."""
    t = translate(tail, -side * slide, 0)
    pts = np.array(t.exterior.segmentize(0.1).coords)
    tip = pts[pts[:, 1].argmin()]  # the swallowtail's lowest point
    d = (tip[0] - pts[:, 0]) * side  # distance in from the tip
    sel = pts[(d > 1.0) & (d < 6.0)]
    bins = np.round(sel[:, 0] / 0.2)
    low = np.array([sel[bins == q][sel[bins == q][:, 1].argmin()] for q in np.unique(bins)])
    a, b = np.polyfit(low[:, 0], low[:, 1], 1)  # the lower edge, y = a x + b
    A, B, C = 1 + a * a, 2 * a * b, b * b - r_ring * r_ring
    disc = B * B - 4 * A * C
    if disc <= 0:
        return t
    x_hit = min(((-B + q * np.sqrt(disc)) / (2 * A) for q in (1, -1)), key=lambda x: abs(x - tip[0]))
    x_far, x_near = x_hit - side * 1.0, tip[0] - side * 2.5  # (it overlaps the tail: one band)
    patch = Polygon([(x_near, a * x_near + b), (x_far, a * x_far + b), (x_far, 0.0), (x_near, 0.0)])
    patch = patch.difference(Point(0, 0).buffer(r_ring, quad_segs=128))
    below = Polygon([(x_near, a * x_near + b), (x_far, a * x_far + b), (x_far, -100), (x_near, -100)])
    band = unary_union([t.difference(below), patch])
    return band.buffer(1.0, join_style="mitre").buffer(-1.0, join_style="mitre")  # no notch where they join


@dataclass
class Drawn:
    region: object  # the whole ribbon, outline included
    yellow: object
    brown: object  # outlines, line_w wide, inside each piece's edge (none along the ring: its circle is the edge)


def drawn(r: Ribbon, r_ring: float, line_w: float, slide: float) -> Drawn:
    backs = [wing(t, side, r_ring, slide) for t, side in zip(r.backs, (-1, 1))]
    front = r.front
    behind = unary_union(backs).difference(front)  # (the sketch's folds don't line up with the slid tails)
    region = unary_union([front, behind])
    ring = Point(0, 0).buffer(r_ring, quad_segs=128)
    yellow = [front.buffer(-line_w, join_style="mitre")]
    for g in backs:  # no outline where a band meets the ring: the ring's own circle is that edge
        yellow.append(unary_union([g, ring]).buffer(-line_w, join_style="mitre").intersection(g).difference(front))
    yellow = V.multi(unary_union(yellow).intersection(region))
    return Drawn(V.multi(region), yellow, V.multi(region.difference(yellow)))


@lru_cache(maxsize=2)
def shapes(p) -> Drawn:
    """The drawn ribbon in the design frame: the sketch registered onto the logo's ribbon (its yellow and the ink
    round it), moved down with the figure, tails slid in and carried on to the ring."""
    from scipy import ndimage as ndi

    from . import art as A
    from . import ears as E

    art = A.load(p)
    px = art.px_mm
    rib = np.isin(art.cls, list(A.RIBBON_FILL))
    ink = art.cls == A.CLASS["ink"]
    near = V.dilated(rib, 0.4 * px)
    target_m = ndi.binary_fill_holes(V.closed(rib | (ink & near), 0.15 * px)) & near
    target = max(V.multi(V.mask_polys(target_m, art.to_mm, px, 0.05, 0.02)).geoms, key=lambda g: g.area)
    r = register(target)
    dy = E.drop(p, art)
    r = Ribbon(translate(r.front, 0, -dy), [translate(t, 0, -dy) for t in r.backs], [translate(f, 0, -dy) for f in r.folds])
    return drawn(r, art.R, p.line_w, p.ribbon_slide)
