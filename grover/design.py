"""Vector composition of the keychain face (mm, origin = ring center).

Relief zones (ascending height): disk < ring < tail < banner < cat (paws rest over the ribbon).
  - ring / disk are exact fitted circles; the other zones are traced and simplified with
    Douglas-Peucker, which keeps ear tips and ribbon corners sharp.
  - Every relief step gets a constant-width brown outline on its raised side (mitred offset).
  - Art details are pulled from the traced raster per zone: eyes become fitted circles,
    letters and paw prints keep `detail_gap` of clear space from every outline.
Output pieces are disjoint (filament, top_z, polygons) that tile the silhouette.
"""

import math
from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from .params import P, Params
from .trace import FILAMENTS, ZONES, Maps, maps, nearest_fill
from .vector import _multi, mask_polys

BASE = {"disk": "white", "ring": "orange", "tail": "yellow", "cat": "white", "banner": "yellow"}
MITRE = dict(join_style="mitre", mitre_limit=2.0)


@dataclass
class Design:
    pieces: list  # [(filament, top_z, MultiPolygon)], disjoint, each rising from core_top
    core: dict  # filament -> MultiPolygon, 0 .. core_top
    silhouette: MultiPolygon
    hole: tuple  # (x, y, r)
    ring: tuple  # (r_out, r_in)
    eyes: list = field(default_factory=list)  # [(x, y, r)]
    zones: dict = field(default_factory=dict)  # zone -> visible polygon


def fit_circle(pts: np.ndarray) -> tuple[float, float, float]:
    """Algebraic (Kasa) least-squares circle."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones_like(x)]
    (cx, cy, c), *_ = np.linalg.lstsq(A, x * x + y * y, rcond=None)
    return cx, cy, math.sqrt(c + cx * cx + cy * cy)


def _edge_pts(a: np.ndarray, b: np.ndarray, m: Maps) -> np.ndarray:
    """mm coords of pixels of mask a that touch mask b."""
    nb = cv2.dilate(b.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.nonzero(a & nb)
    return np.c_[m.to_mm(xs, ys)]


def _circle(x, y, r) -> Polygon:
    return Point(x, y).buffer(r, quad_segs=64)


def _keep(g, p: Params, min_w=None, min_area=None) -> MultiPolygon:
    """Drop pieces too thin or too small to print."""
    min_w = p.min_detail if min_w is None else min_w
    min_area = p.min_detail_area if min_area is None else min_area
    return MultiPolygon([x for x in _multi(g).geoms
                         if x.area >= min_area and not x.buffer(-min_w / 2).is_empty])


def _fill_small_holes(g, max_area: float) -> MultiPolygon:
    return MultiPolygon([Polygon(x.exterior, [r for r in x.interiors if Polygon(r).area > max_area])
                         for x in _multi(g).geoms])


def _sharp_tip(g, r: float, reach: float = 4.0, extend: float = 0.5):
    """Rebuild an ear's tip where its two straight edges meet (art fur notches removed)."""
    g = g.buffer(0)
    pts = np.array([q for x in _multi(g.segmentize(0.1)).geoms for q in x.exterior.coords])
    top = pts[pts[:, 1].argmax()]
    d = np.hypot(*(pts - top).T)
    win = pts[(d >= r) & (d <= reach) & (pts[:, 1] > top[1] - reach)]
    sides = [win[win[:, 0] < top[0]], win[win[:, 0] > top[0]]]
    if any(len(s) < 5 for s in sides):
        return g

    def line(q):  # point + unit direction (PCA)
        c = q.mean(0)
        _, _, vt = np.linalg.svd(q - c)
        return c, vt[0]

    (c1, d1), (c2, d2) = line(sides[0]), line(sides[1])
    A = np.c_[d1, -d2]
    if abs(np.linalg.det(A)) < 1e-6:
        return g
    t = np.linalg.solve(A, c2 - c1)
    apex = c1 + t[0] * d1
    dist = np.hypot(*(apex - top))
    if dist > extend:  # don't grow a needle: stop a little past the art's tip
        apex = top + (apex - top) * extend / dist
    zone = Point(*top).buffer(r, quad_segs=32)
    base = _multi(g.difference(zone))
    rim = [q for x in base.geoms for q in x.exterior.coords if math.dist(q, top) <= r + 1e-3]
    tri = Polygon([tuple(apex), *rim]).convex_hull
    return unary_union([base, tri]).buffer(0)


def _close_open(g, close: float, open_: float, **kw):
    """Fill gaps narrower than 2*close, then drop slivers thinner than 2*open_."""
    g = g.buffer(close, **kw).buffer(-close, **kw)
    return g.buffer(-open_, **kw).buffer(open_, **kw)


@lru_cache(maxsize=2)
def design(p: Params = P) -> Design:
    m = maps(p)
    Zid = {z: ZONES.index(z) + 1 for z in ZONES}
    brown, white, orange = (FILAMENTS.index(f) + 1 for f in ("brown", "white", "orange"))
    valid = m.zone > 0

    # --- ring / disk circles, and recentering --------------------------------------------
    ring_m, disk_m = m.zone == Zid["ring"], m.zone == Zid["disk"]
    cx, cy, r_out = fit_circle(_edge_pts(ring_m, ~valid, m))
    _, _, r_in = fit_circle(_edge_pts(ring_m, disk_m, m))

    def T(g):
        return shapely.affinity.translate(g, -cx, -cy)

    def zmask(z):
        return m.zone == Zid[z]

    zones = {
        "disk": _circle(0, 0, r_in),
        "ring": _circle(0, 0, r_out).difference(_circle(0, 0, r_in)),
        # mitred close/open removes art noise but keeps ear tips and ribbon corners sharp
        **{z: _fill_small_holes(_close_open(T(mask_polys(zmask(z), m, p)), p.zone_clean, p.zone_clean,
                                            join_style="mitre", mitre_limit=5.0), p.zone_hole_fill)
           for z in ("tail", "cat", "banner")},
    }
    # Grover's cheeks: round-smooth the fur tufts; above the eye line keep the sharp ears
    cat = zones["cat"]
    ears_y = cat.bounds[3] - p.ear_keep
    soft = _close_open(cat, p.cheek_smooth, p.cheek_smooth)
    ears = cat.intersection(box(-100, ears_y - 0.5, 100, 100)).simplify(p.ear_simplify)
    ears = ears.intersection(cat.buffer(0.05)).intersection(box(-100, ears_y - 0.3, 100, 100))
    cx_cat = cat.centroid.x
    ears = unary_union([_sharp_tip(ears.intersection(b), p.ear_tip_trim)
                        for b in (box(-100, -100, cx_cat, 100), box(cx_cat, -100, 100, 100))])
    zones["cat"] = unary_union([soft.difference(box(-100, ears_y, 100, 100)), ears])

    order = list(ZONES)  # ascending height
    # lower zones reach slightly under higher ones so the stack never cracks open
    for i, z in enumerate(order):
        above = unary_union([zones[h] for h in order[i + 1:]])
        zones[z] = unary_union([zones[z], zones[z].buffer(p.underlap, **MITRE).intersection(above)])

    hole = (0.0, r_out - p.hole_wall - p.hole_r, p.hole_r)
    hole_poly = _circle(*hole)
    hole_band = _circle(hole[0], hole[1], p.hole_r + p.line_w)
    sil = _multi(unary_union(list(zones.values())).difference(hole_poly))
    world = box(-100, -100, 100, 100)

    def art(f: int, z: str):
        return T(mask_polys((m.fil == f) & zmask(z), m, p))

    # Grover's fur colors with the art linework filled in from the nearest fur color,
    # so orange/white patches run right up to the generated outline.
    fur = nearest_fill(m.fil, (m.fil != brown) & (m.fil > 0))

    pieces, vis_zones, eyes = [], {}, []
    higher = Polygon()
    for z in reversed(order):  # highest first
        h = p.zone_top[z]
        vis = zones[z].difference(higher).difference(hole_band)
        outside = world.difference(unary_union([zones[z], higher]))
        outside = outside.buffer(-0.05, **MITRE).buffer(0.05, **MITRE)  # no slivers -> no spikes
        band = vis.intersection(outside.buffer(p.line_w, **MITRE))
        inner = vis.difference(band)
        clear = inner.buffer(-p.detail_gap, **MITRE)  # where details may go
        vis_zones[z] = vis

        details = []  # (filament, polys), earlier wins
        if z == "cat":
            eye_c = []
            for g in _keep(art(brown, z).intersection(clear), p).geoms:
                (ex, ey), er = cv2.minEnclosingCircle(np.array(g.exterior.coords, np.float32))
                round_ = 4 * math.pi * g.area / g.exterior.length ** 2
                if p.eye_r_range[0] <= er <= p.eye_r_range[1] and round_ > 0.6:
                    eye_c.append((g.area, float(ex), float(ey), float(er)))
            eyes = sorted(e[1:] for e in sorted(eye_c, reverse=True)[:2])
            eye_polys = unary_union([_circle(*e) for e in eyes])
            glints = []
            for g in art(white, z).geoms:
                c = g.centroid
                for ex, ey, er in eyes:
                    if math.hypot(c.x - ex, c.y - ey) < er - 0.2 and g.area > math.pi * 0.15 ** 2:
                        gr = max(p.eye_glint_min_r, math.sqrt(g.area / math.pi))
                        gr = min(gr, er - math.hypot(c.x - ex, c.y - ey) - 0.3)
                        if gr > 0.2:
                            glints.append(_circle(c.x, c.y, gr))
            details.append(("white", unary_union(glints)))
            details.append(("brown", eye_polys.intersection(inner)))
            other = art(brown, z).difference(eye_polys.buffer(0.3)).intersection(clear)
            solid = _keep(other.buffer(-p.min_detail / 2).buffer(p.min_detail / 2), p)  # nose etc.
            nose = max(solid.geoms, key=lambda g: g.area) if not solid.is_empty else None
            if nose is not None:  # a clean solid nose, no glint
                solid = MultiPolygon([g.convex_hull if g is nose else Polygon(g.exterior) for g in solid.geoms])
                nose = nose.convex_hull
            mouth = Polygon()
            if nose is not None:  # thin lines right under the nose are the mouth; elsewhere whiskers
                near = _circle(nose.centroid.x, nose.centroid.y - 0.8, p.mouth_reach)
                lines = other.difference(solid).intersection(near)
                mouth = _keep(lines.buffer(p.mouth_thicken), p, min_w=0.3, min_area=0.05)
            face_lines = _fill_small_holes(unary_union([solid, mouth]), 1.0)  # no glint trapped in the nose
            details.append(("brown", face_lines.intersection(clear)))
            fur_orange = T(mask_polys((fur == orange) & zmask(z), m, p))
            patches = _close_open(fur_orange, p.patch_close, p.patch_open).intersection(inner)
            patches = _keep(patches, p, min_w=0.5, min_area=p.min_patch_area)
            # tiny white islands left between orange fur and the outline become orange
            rest = inner.difference(unary_union([band, patches] + [g for _, g in details]))
            islands = [g for g in _multi(rest).geoms if g.area < p.min_white_island]
            details.append(("orange", unary_union([patches, *islands])))
        elif z in ("ring", "banner"):
            d = art(brown, z).intersection(clear)
            if z == "ring":  # the top paw print gives way to the keyring hole
                d = MultiPolygon([g for g in _multi(d).geoms
                                  if g.centroid.distance(Point(hole[:2])) > 4.0])
            details.append(("brown", _keep(d, p)))

        taken = band
        pieces.append(("brown", h, _multi(band)))
        for f, g in details:
            g = _multi(g.difference(taken))
            if not g.is_empty:
                pieces.append((f, h, g))
                taken = taken.union(g)
        base = _multi(inner.difference(taken))
        slivers = [g for g in base.geoms if g.buffer(-p.min_detail / 2).is_empty]  # unprintable
        if slivers:
            pieces.append(("brown", h, MultiPolygon(slivers)))  # merge into the outline
            base = MultiPolygon([g for g in base.geoms if not g.buffer(-p.min_detail / 2).is_empty])
        pieces.append((BASE[z], h, base))
        higher = higher.union(zones[z])

    ring_h = p.zone_top["ring"]
    pieces.append(("brown", ring_h, _multi(hole_band.difference(hole_poly).intersection(sil))))
    pieces = [(f, h, _multi(g.intersection(sil))) for f, h, g in pieces]
    pieces = [(f, h, g) for f, h, g in pieces if not g.is_empty]

    ribbon = unary_union([zones["banner"], zones["tail"]]).intersection(sil)
    core = {"yellow": _multi(ribbon), "orange": _multi(sil.difference(ribbon))}
    return Design(pieces=pieces, core=core, silhouette=sil, hole=hole, ring=(r_out, r_in),
                  eyes=eyes, zones=vis_zones)
