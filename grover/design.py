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
from . import sketch
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


def _sharp_tip(g, r: float, extend: float = 1.0):
    """Rebuild an ear tip: continue each edge (its direction just below the tip) until they meet."""
    g = g.buffer(0)
    pts = np.array([q for x in _multi(g.segmentize(0.05)).geoms for q in x.exterior.coords])
    top = pts[pts[:, 1].argmax()]
    d = np.hypot(*(pts - top).T)
    band_ = pts[(d >= r) & (d <= r + 1.2) & (pts[:, 1] > top[1] - r - 1.5)]
    sides = [band_[band_[:, 0] < top[0]], band_[band_[:, 0] > top[0]]]
    if any(len(s_) < 4 for s_ in sides):
        return g
    rays = []
    for s_ in sides:
        c = s_.mean(0)
        _, _, vt = np.linalg.svd(s_ - c)
        v = vt[0] if np.dot(vt[0], top - c) > 0 else -vt[0]  # point toward the tip
        start = s_[np.argmin(np.abs(np.hypot(*(s_ - top).T) - r))]  # on the outline, r from the tip
        rays.append((start, v))
    (c1, v1), (c2, v2) = rays
    A = np.c_[v1, -v2]
    if abs(np.linalg.det(A)) < 1e-6:
        return g
    t = np.linalg.solve(A, c2 - c1)
    apex = c1 + t[0] * v1
    dist = np.hypot(*(apex - top))
    if dist > extend:
        apex = top + (apex - top) * extend / dist
    tri = Polygon([tuple(c1), tuple(apex), tuple(c2)]).buffer(0)
    return unary_union([g, tri]).buffer(0)


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
    # Grover comes from the hand-traced sketch: his head is hidden behind the ribbon except
    # for the paws, which rest on top of it.
    k = sketch.load(round(r_out, 6))
    head = k.head
    top = head.bounds[3]
    ear_box = box(-100, top - p.ear_len, 100, 100)
    ears = [_sharp_tip(head.intersection(ear_box).intersection(b), p.ear_tip_trim)
            for b in (box(-100, -100, head.centroid.x, 100), box(head.centroid.x, -100, 100, 100))]
    head = unary_union([head.difference(ear_box), *ears])
    zones["cat"] = unary_union([head.difference(zones["banner"]), *k.paws])

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
            eyes = k.eyes
            eye_polys = unary_union([_circle(*e) for e in eyes])
            glints = unary_union([_circle(x, y, max(r, p.eye_glint_min_r)) for x, y, r in k.glints])
            strokes = k.lines.buffer(p.stroke_w / 2, cap_style="round", join_style="round")
            strokes = strokes.difference(eye_polys.buffer(p.eye_clear))  # eyes stay perfect circles
            details.append(("white", glints.intersection(eye_polys)))
            details.append(("brown", unary_union([eye_polys, k.nose, strokes]).intersection(inner)))
            fur_orange = T(mask_polys((fur == orange) & (m.zone > 0), m, p))
            patches = _close_open(fur_orange, p.patch_close, p.patch_open).intersection(inner)
            patches = _keep(patches, p, min_w=0.5, min_area=p.min_patch_area)
            # tiny white islands left between orange fur and the lines become orange
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
