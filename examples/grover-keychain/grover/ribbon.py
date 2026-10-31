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


def _smooth(pts: list) -> list:
    """A sketch edge (a polyline between two corners) as a smooth curve through its points: Onshape exported each
    spline as a few straight segments, which showed as kinks along the banner."""
    from scipy.interpolate import CubicSpline

    c = np.array(pts, dtype=float)
    if len(c) < 3:
        return pts
    t = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(c, axis=0).T))])
    f = CubicSpline(t, c, bc_type="natural")
    return [tuple(q) for q in f(np.linspace(0, t[-1], max(20, int(t[-1] / 0.3))))]


@lru_cache(maxsize=1)
def raw():
    """(front, [left tail, right tail], folds) in sketch units, each grown by the sketch's outline thickness so it
    includes its outline. The sketch draws both edges of each outline and one tail; the ribbon is symmetric."""
    msp = ezdxf.readfile(SKETCH).modelspace()
    lines = [shapely.set_precision(LineString(_smooth([(q[0], q[1]) for q in e.get_points("xy")])), 1e-3)
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


def v_notch(tail: Polygon, side: int, out: float, depth: float) -> Polygon:
    """The swallowtail's end as a uniform V: straight arms from the upper prong's tip and the lower tip (moved `out`
    outward) to a point `depth` in from the middle of the line between them."""
    c = np.array(tail.simplify(0.01).exterior.coords)[:-1]
    top = c[(c[:, 0] * side).argmax()]  # the upper prong's tip
    low = c[c[:, 1].argmin()] + (side * out, 0)  # the lower tip
    d = low - top
    n = np.array([-d[1], d[0]]) / np.hypot(*d)
    n *= -np.sign(n[0] * side)  # in, away from the end
    apex = (top + low) / 2 + n * depth
    return unary_union([tail, Point(low)]).convex_hull.difference(Polygon([top, apex, low, low + n * -5, top + n * -5]))


@dataclass
class Drawn:
    region: object  # the whole ribbon, outline included
    yellow: object
    brown: object  # outlines, line_w wide: round each piece, along each fold's crease (none along the ring)
    folds: list = None  # [left, right] footprints, outline and the whole crease line included
    tails: list = None  # [left, right] footprints, outline included


def drawn(r: Ribbon, r_ring: float, line_w: float, slide: float, lift: float, fold_ring: float,
          tail_out: float, notch_depth: float) -> Drawn:
    """The banner in front; behind each end, the back band: its tail (slid in, lifted) below a straight crease from
    the banner's lower corner to the ring, and above the crease the fold, which the banner and the ring close (the
    logo's triangle). The crease meets the ring `fold_ring` below the banner, and the tail's lower edge runs to the
    same point: tail, fold and ring meet there. The tail's end is a uniform V (v_notch). One line between neighbours: the
    bands don't outline themselves against the banner or the ring, and the crease is a single line."""
    front = r.front
    ring = Point(0, 0).buffer(r_ring, quad_segs=256)  # (the silhouette's circle, exactly)
    fc = np.array(front.exterior.coords)
    meets = shapely.get_coordinates(front.exterior.intersection(ring.exterior))
    pieces, bands, creases, folds, tails = [], [], [], [], []
    for tail, fold, side in zip(r.backs, sorted(r.folds, key=lambda f: f.centroid.x), (-1, 1)):
        fp = np.array(fold.exterior.coords)
        corner = fc[np.argmin(np.hypot(*(fc - fp[(fp[:, 0] * side).argmax()]).T))]  # banner's lower corner
        p = meets[meets[:, 0] * side > 0]
        p = p[p[:, 1].argmin()]  # where the banner's lower edge meets the ring
        a = np.arctan2(p[1], p[0]) - side * fold_ring / r_ring
        h = np.array([np.cos(a), np.sin(a)]) * r_ring  # crease, tail and fold meet the ring here
        t = v_notch(translate(tail, -side * slide, lift), side, tail_out, notch_depth)
        tp = np.array(t.exterior.coords)
        bottom = tp[tp[:, 1] < tp[:, 1].min() + 1e-6]
        low = bottom[(bottom[:, 0] * side).argmax()]  # the tail's lower tip
        on = h + (h - corner) / np.hypot(*(h - corner)) * 3.0  # (carried on into the ring)
        under = h + (h - low) / np.hypot(*(h - low)) * 3.0
        above = Polygon([corner, on, on + (0, 20), corner + (0, 20)])
        below = Polygon([low, under, under - (0, 20), low - (0, 20)])
        gap = above.difference(ring).difference(front)
        near = Point(corner + 0.9 * (h - corner) + (0, 0.02))
        fold_piece = min(getattr(gap, "geoms", [gap]), key=lambda g: g.distance(near))
        whole = unary_union([t, Polygon([low, h, corner])]).difference(below).difference(ring).difference(front)
        body = whole.difference(above)  # the tail (and the upper prong)
        band = unary_union([fold_piece, body])
        pieces += [fold_piece, body]
        bands.append(band)
        folds.append(fold_piece)
        tails.append(body)
        # the crease starts flush with the banner's outer edge (a square end would leave a step against it)
        fs = np.array(front.simplify(0.01).exterior.coords)[:-1]
        k = np.argmin(np.hypot(*(fs - corner).T))
        e = max((fs[k - 1], fs[(k + 1) % len(fs)]), key=lambda v: v[1]) - fs[k]  # up the banner's outer edge
        e = e / np.hypot(*e)
        n = np.array([-e[1], e[0]]) * np.sign(np.dot([-e[1], e[0]], h - corner))  # toward the ring
        inside = Polygon([corner + e * 20, corner - e * 20, corner - e * 20 + n * 20, corner + e * 20 + n * 20])
        start = corner - (h - corner) / np.hypot(*(h - corner)) * 3.0
        creases.append((LineString([start, on]), inside, band))
    behind = unary_union(pieces)
    region = unary_union([front, behind])
    brown = [front.difference(front.buffer(-line_w, join_style="mitre"))]
    for g in bands:  # no outline of its own against the ring or the banner: their edges are that line
        cover = unary_union([g, ring.buffer(0.01), front.buffer(0.01)])  # (grown: no hairline gap left to outline)
        brown.append(g.difference(cover.buffer(-line_w, join_style="mitre", mitre_limit=1.5)))
    lines = [c.buffer(line_w / 2, cap_style="flat").intersection(inside).intersection(band)
             for c, inside, band in creases]
    brown = V.multi(unary_union(brown + lines).intersection(region))
    folds = [V.multi(unary_union([f, c])) for f, c in zip(folds, lines)]  # the crease is the fold's edge
    tails = [V.multi(t.difference(f)) for t, f in zip(tails, folds)]
    return Drawn(V.multi(region), V.multi(region.difference(brown)), brown, folds, tails)


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
    return drawn(r, art.R, p.line_w, p.ribbon_slide, p.ribbon_lift, p.fold_ring, p.tail_out, p.notch_depth)
