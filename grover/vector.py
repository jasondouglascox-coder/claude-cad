"""Raster maps -> non-overlapping 2D polygons (shapely, mm) -> extruded build123d solids."""

import cv2
import numpy as np
import segno
import shapely
from build123d import Face, Part, Pos, Vector, Wire, extrude
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from .params import P, Params
from .trace import FILAMENTS, ZONES, Maps


def mask_polys(mask: np.ndarray, m: Maps, p: Params = P) -> MultiPolygon:
    """Smooth sub-pixel outline of a boolean mask, in mm."""
    up = p.vec_upsample
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), p.vec_smooth * m.px_mm)
    f = cv2.resize(f, None, fx=up, fy=up, interpolation=cv2.INTER_LINEAR)
    bw = (f > 0.5).astype(np.uint8)
    contours, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return MultiPolygon()
    hier = hier[0]
    eps = p.vec_tol * m.px_mm * up

    def ring(c):
        c = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)
        x, y = (c[:, 0] + 0.5) / up - 0.5, (c[:, 1] + 0.5) / up - 0.5
        return list(zip(*m.to_mm(x, y)))

    polys = []
    for i, h in enumerate(hier):
        if h[3] != -1:
            continue
        outer = ring(contours[i])
        if len(outer) < 3:
            continue
        holes, j = [], h[2]
        while j != -1:
            r = ring(contours[j])
            if len(r) >= 3:
                holes.append(r)
            j = hier[j][0]
        polys.append(Polygon(outer, holes).buffer(0))
    return _multi(unary_union(polys))


def _multi(g) -> MultiPolygon:
    if g.is_empty:
        return MultiPolygon()
    if isinstance(g, Polygon):
        return MultiPolygon([g])
    if isinstance(g, MultiPolygon):
        return g
    return MultiPolygon([x for x in getattr(g, "geoms", []) if isinstance(x, Polygon)])


def _drop_slivers(g, p: Params) -> MultiPolygon:
    return MultiPolygon([x for x in _multi(g).geoms if x.area >= p.vec_min_area])


def hole(m: Maps, p: Params = P) -> Polygon:
    return Point(*m.hole_mm).buffer(p.hole_r, quad_segs=32)


def qr_shapes(p: Params = P) -> tuple[Polygon, MultiPolygon]:
    """(white panel, dark modules) at the origin, mirrored so the code reads from the back."""
    q = segno.make(p.url, error=p.qr_error, micro=False, boost_error=False)
    mat = [[bool(v) for v in row] for row in q.matrix]
    n, s, g = len(mat), p.qr_module, p.qr_grow
    x0, y0 = -n * s / 2, p.qr_y + n * s / 2
    cells = [box(x0 + c * s - g, y0 - (r + 1) * s - g, x0 + (c + 1) * s + g, y0 - r * s + g)
             for r, row in enumerate(mat) for c, v in enumerate(row) if v]
    mods = shapely.affinity.scale(unary_union(cells), xfact=-1, origin=(0, 0))
    half = (n + 2 * p.qr_quiet) * s / 2
    panel = box(-half, p.qr_y - half, half, p.qr_y + half).buffer(-p.qr_corner).buffer(p.qr_corner, quad_segs=16)
    return panel, _multi(mods)


def layout(m: Maps, p: Params = P) -> dict:
    """{'top': [(filament, top_z, polys)], 'core': {filament: polys}, 'silhouette': polys}"""
    valid = m.fil > 0
    sil = _multi(mask_polys(valid, m, p).difference(hole(m, p)))

    order = ["brown", "white", "yellow", "orange"]
    top, placed = [], Polygon()
    for f in order:
        fi = FILAMENTS.index(f) + 1
        for zi, z in enumerate(ZONES, start=1):
            mask = (m.fil == fi) & (m.zone == zi)
            if mask.sum() < 4:
                continue
            g = mask_polys(mask, m, p).buffer(p.vec_gap, join_style="mitre")
            g = _drop_slivers(g.intersection(sil).difference(placed), p)
            if g.is_empty:
                continue
            placed = unary_union([placed, g])
            top.append((f, p.zone_top[z], g))

    ribbon = np.isin(m.zone, [ZONES.index("banner") + 1, ZONES.index("tail") + 1])
    yel = _drop_slivers(mask_polys(ribbon, m, p).buffer(p.vec_gap).intersection(sil), p)
    core = {"yellow": yel, "orange": _drop_slivers(sil.difference(yel), p)}
    return {"top": top, "core": core, "silhouette": sil, "gaps": sil.difference(placed).area}


def face(poly: Polygon) -> Face:
    """Planar face with +Z normal (exterior forced CCW; a CW face extrudes toward -Z)."""
    poly = shapely.geometry.polygon.orient(poly, 1.0)

    def wire(coords):
        pts = [Vector(x, y, 0) for x, y in list(coords)[:-1]]
        return Wire.make_polygon(pts, close=True)

    return Face(wire(poly.exterior.coords), [wire(r.coords) for r in poly.interiors])


def prisms(polys, z0: float, z1: float) -> list:
    # a tiny opening splits pinch points (hole touching outline), which OCC rejects
    polys = _multi(polys).buffer(-0.002, join_style="mitre").buffer(0.002, join_style="mitre")
    out = []
    for g in _multi(polys).geoms:
        pr = Pos(0, 0, z0) * extrude(face(g), z1 - z0)
        if not pr.is_valid:
            raise ValueError(f"invalid prism at {g.representative_point()} z={z0}..{z1}")
        out.append(pr)
    return out
