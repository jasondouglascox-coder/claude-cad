"""Vector composition of the keychain face (mm, origin = ring center).

Zones in front-to-back priority: disk < tail < ring < banner < cat < paw, printed as three layers
(backdrop + ribbon flaps / ring + ribbon + face / paws). Outlines go on the higher-priority side.
  - ring / disk are exact fitted circles; the other zones are traced and simplified with
    Douglas-Peucker, which keeps ear tips and ribbon corners sharp.
  - Every relief step gets a constant-width brown outline on its raised side (mitred offset).
  - Art details are pulled from the traced raster per zone: eyes become fitted circles,
    letters and paw prints keep `detail_gap` of clear space from every outline.
Output pieces are disjoint (filament, top_z, polygons) that tile the silhouette.
"""

import math
from dataclasses import dataclass, field, replace
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

BASE = {"disk": "white", "ring": "orange", "tail": "yellow", "cat": "white", "banner": "yellow", "paw": "white"}
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


def _wing(t, side: int, r_out: float, p: Params):
    """Slide a ribbon tail toward the middle, and carry its lower edge on until it meets the ring."""
    t = shapely.affinity.translate(t, -side * p.tail_in, 0)
    pts = np.array(t.exterior.segmentize(0.1).coords)
    tip = pts[pts[:, 1].argmin()]  # lowest point: bottom of the swallowtail
    d = (tip[0] - pts[:, 0]) * side  # distance from the tip toward the middle
    sel = pts[(d > 1.0) & (d < 6.0)]
    bins = np.round(sel[:, 0] / 0.2)
    low = np.array([sel[bins == q][sel[bins == q][:, 1].argmin()] for q in np.unique(bins)])
    a, b = np.polyfit(low[:, 0], low[:, 1], 1)  # the lower edge, y = a x + b
    A, B, C = 1 + a * a, 2 * a * b, b * b - r_out * r_out
    disc = B * B - 4 * A * C
    if disc <= 0:
        return t
    roots = [(-B + q * math.sqrt(disc)) / (2 * A) for q in (1, -1)]
    x_hit = min(roots, key=lambda x: abs(x - tip[0]))  # where the edge reaches the ring
    x_far = x_hit - side * 1.0
    x_near = tip[0] - side * 5.0  # still on the tail's own lower edge
    # above the extended edge, from the tail to just past the ring, below the ring's center line;
    # the ring is drawn over the tail, so only the sliver between edge and ring shows
    patch = Polygon([(x_near, a * x_near + b), (x_far, a * x_far + b), (x_far, 0.0), (x_near, 0.0)])
    patch = patch.difference(Point(0, 0).buffer(r_out - p.tail_tuck, quad_segs=64))
    below = Polygon([(x_near, a * x_near + b), (x_far, a * x_far + b), (x_far, -100), (x_near, -100)])
    return unary_union([t.difference(below), patch])  # one straight lower edge


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
    # The ribbon comes from its hand-traced sketch, registered onto the traced ribbon.
    rb = sketch.load_ribbon(unary_union([zones["banner"], zones["tail"]]).wkt)

    # Grover and the ribbon sit lower in the ring than in the logo, filling the orange below
    dy = -p.figure_drop * 2 * r_out

    def F(g):
        return shapely.affinity.translate(g, 0, dy)

    zones["banner"] = F(rb.front)
    wings = [_wing(F(t), side, r_out, p) for t, side in zip(rb.tails, (-1, 1))]
    tails = unary_union([*wings, *[F(f) for f in rb.folds]]).difference(zones["banner"])
    # tails tuck under the ring (which is drawn over them), so extend them beneath it
    zones["tail"] = unary_union([tails, tails.buffer(p.tail_tuck, **MITRE).intersection(zones["ring"])])
    # hairline gaps where the sketched tails meet the fitted ring belong to the tails
    every = unary_union(list(zones.values()))
    gaps = every.buffer(p.gap_close, **MITRE).buffer(-p.gap_close, **MITRE).difference(every)
    zones["tail"] = unary_union([zones["tail"], gaps.buffer(0.01)])

    # Grover comes from the hand-traced sketch: his head is hidden behind the ribbon except
    # for the paws, which rest on top of it.
    k = sketch.load(round(r_out, 6))
    k = sketch.Sketch(head=F(k.head), paws=[F(g) for g in k.paws], nose=F(k.nose), lines=F(k.lines),
                      eyes=[(x, y + dy, r) for x, y, r in k.eyes],
                      glints=[(x, y + dy, r) for x, y, r in k.glints])
    head = k.head
    top = head.bounds[3]
    ear_box = box(-100, top - p.ear_len, 100, 100)
    ears = [_sharp_tip(head.intersection(ear_box).intersection(b), p.ear_tip_trim)
            for b in (box(-100, -100, head.centroid.x, 100), box(head.centroid.x, -100, 100, 100))]
    head = unary_union([head.difference(ear_box), *ears])
    above = max(_multi(head.difference(zones["banner"])).geoms, key=lambda g: g.area)  # drop the bit below the ribbon
    zones["cat"] = above
    zones["paw"] = unary_union(k.paws)

    # specks of the backdrop circle peeking out under the ribbon become ring
    shown = _multi(zones["disk"].difference(unary_union([zones[z] for z in ("tail", "banner", "cat")])))
    specks = [g for g in shown.geoms if g.area < p.min_zone_area * 3]
    if specks:
        zones["disk"] = zones["disk"].difference(unary_union(specks).buffer(0.01))
        zones["ring"] = unary_union([zones["ring"], *specks])

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
        # letters keep a finer trace (curves stay curves); everything else uses the default
        pz = replace(p, vec_tol=p.letter_tol, vec_smooth=p.letter_blur) if z == "banner" else p
        g = T(mask_polys((m.fil == f) & zmask(z), m, pz))
        return F(g) if z in ("tail", "banner", "cat") else g

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
            # nose stands up to paw height; eyes (with glints) sit between face and nose
            details.append(("white", glints.intersection(eye_polys), p.eye_top))
            details.append(("brown", k.nose.intersection(inner), p.zone_top["paw"]))
            details.append(("brown", eye_polys.intersection(inner), p.eye_top))
            details.append(("brown", strokes.intersection(inner)))
            near_cat = cv2.dilate(zmask("cat").astype(np.uint8), np.ones((int(m.px_mm), int(m.px_mm)), np.uint8)) > 0
            fur_orange = F(T(mask_polys((fur == orange) & near_cat, m, p)))
            patches = _close_open(fur_orange, p.patch_close, p.patch_open).intersection(inner)
            patches = _keep(patches, p, min_w=0.5, min_area=p.min_patch_area)
            # tiny white islands left between orange fur and the lines become orange
            rest = inner.difference(unary_union([band, patches] + [d_[1] for d_ in details]))
            islands = [g for g in _multi(rest).geoms if g.area < p.min_white_island]
            details.append(("orange", unary_union([patches, *islands])))
        elif z in ("ring", "banner"):
            d = art(brown, z).intersection(clear)
            if z == "ring":  # the top paw print gives way to the keyring hole
                d = MultiPolygon([g for g in _multi(d).geoms
                                  if g.centroid.distance(Point(hole[:2])) > 4.0])
            if z == "banner":  # smooth the traced letter edges (round open + close)
                r = p.letter_smooth
                d = d.buffer(r).buffer(-2 * r).buffer(r).intersection(clear)
            # ribbon letters stand proud of the yellow; ring paw prints keep the ring's full height
            details.append(("brown", _keep(d, p), h + p.letter_raise if z == "banner" else h))

        taken = band
        pieces.append(("brown", h, _multi(band)))
        for f, g, *top in details:
            g = _multi(g.difference(taken))
            if not g.is_empty:
                pieces.append((f, top[0] if top else h, g))
                taken = taken.union(g)
        base = _multi(inner.difference(taken))
        slivers = [g for g in base.geoms if g.buffer(-p.min_detail / 2).is_empty]  # unprintable
        if slivers:
            pieces.append(("brown", h, MultiPolygon(slivers)))  # merge into the outline
            base = MultiPolygon([g for g in base.geoms if not g.buffer(-p.min_detail / 2).is_empty])
        # the ring's orange sinks below its outlines and paw prints
        pieces.append((BASE[z], h - p.ring_sink if z == "ring" else h, base))
        higher = higher.union(zones[z])

    # the ring around the keyring hole is flush with the ring's orange: no lip for the clasp to catch
    ring_h = p.zone_top["ring"] - p.ring_sink
    pieces.append(("brown", ring_h, _multi(hole_band.difference(hole_poly).intersection(sil))))
    pieces = [(f, h, _multi(g.intersection(sil))) for f, h, g in pieces]
    pieces = [(f, h, g) for f, h, g in pieces if not g.is_empty]

    # base layer seen from the back: the full orange ring disc, yellow wherever the ribbon sticks out
    disc = _circle(0, 0, r_out)
    core = {"orange": _multi(sil.intersection(disc)), "yellow": _multi(sil.difference(disc))}
    return Design(pieces=pieces, core=core, silhouette=sil, hole=hole, ring=(r_out, r_in),
                  eyes=eyes, zones=vis_zones)
