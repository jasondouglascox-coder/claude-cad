"""Raster masks <-> shapely polygons (mm) <-> build123d solids, plus mm-sized morphology helpers."""
import cv2
import numpy as np
import shapely
from build123d import Face, Pos, Vector, Wire, extrude
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union


def disk(r_px: float) -> np.ndarray:
    r = max(1, int(round(r_px)))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return ((x * x + y * y) <= r_px * r_px + 0.5).astype(np.uint8)


def opened(m: np.ndarray, r_px: float) -> np.ndarray:
    """Drops anything narrower than 2 r."""
    return cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, disk(r_px)) > 0


def closed(m: np.ndarray, r_px: float) -> np.ndarray:
    return cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, disk(r_px)) > 0


def dilated(m: np.ndarray, r_px: float) -> np.ndarray:
    return cv2.dilate(m.astype(np.uint8), disk(r_px)) > 0


def eroded(m: np.ndarray, r_px: float) -> np.ndarray:
    return cv2.erode(m.astype(np.uint8), disk(r_px)) > 0


def components(m: np.ndarray, min_px: int = 1) -> list[np.ndarray]:
    n, lab = cv2.connectedComponents(m.astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):
        c = lab == i
        if c.sum() >= min_px:
            out.append(c)
    return out


def multi(g) -> MultiPolygon:
    if g is None or g.is_empty:
        return MultiPolygon()
    if isinstance(g, Polygon):
        return MultiPolygon([g])
    if isinstance(g, MultiPolygon):
        return g
    return MultiPolygon([x for x in getattr(g, "geoms", []) if isinstance(x, Polygon) and not x.is_empty])


def mask_polys(mask: np.ndarray, to_mm, px_mm: float, smooth_mm: float, tol_mm: float, up: int = 2) -> MultiPolygon:
    """Sub-pixel outline of a boolean mask in mm: blur, upsample, threshold, contour, Douglas-Peucker."""
    f = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), max(smooth_mm * px_mm, 0.3))
    f = cv2.resize(f, None, fx=up, fy=up, interpolation=cv2.INTER_LINEAR)
    bw = (f > 0.5).astype(np.uint8)
    contours, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return MultiPolygon()
    hier = hier[0]
    eps = tol_mm * px_mm * up

    def ring(c):
        c = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(float)
        x, y = (c[:, 0] + 0.5) / up - 0.5, (c[:, 1] + 0.5) / up - 0.5
        return list(zip(*to_mm(x, y)))

    polys = []
    for i, h in enumerate(hier):
        if h[3] != -1:
            continue
        outer = ring(contours[i])
        if len(outer) < 3:
            continue
        holes, j = [], h[2]
        while j != -1:
            rr = ring(contours[j])
            if len(rr) >= 3:
                holes.append(rr)
            j = hier[j][0]
        polys.append(Polygon(outer, holes).buffer(0))
    return multi(unary_union(polys))


def clean(g, min_area: float = 1e-3):
    """Drop slivers and single-point pinches that make OCC solids invalid."""
    g = multi(g).buffer(-0.002, join_style="mitre").buffer(0.002, join_style="mitre")
    g = multi(g.simplify(0.0001))  # near-duplicate and in-line vertices make bad faces and mesh T-junctions
    return multi(unary_union([Polygon(q.exterior, [r for r in q.interiors if Polygon(r).area > min_area])
                              for q in multi(g).geoms if q.area > min_area]))


def face(poly: Polygon) -> Face:
    poly = shapely.geometry.polygon.orient(poly, 1.0)

    def wire(coords):
        return Wire.make_polygon([Vector(x, y, 0) for x, y in list(coords)[:-1]], close=True)

    return Face(wire(poly.exterior.coords), [wire(r.coords) for r in poly.interiors])


def prisms(polys, z0: float, z1: float, cleaned: bool = False) -> list:
    out = []
    for g in (multi(polys) if cleaned else clean(polys)).geoms:
        pr = Pos(0, 0, z0) * extrude(face(g), z1 - z0)
        if not pr.is_valid:  # a borderline face (near-coincident vertices): once more on a 0.1 micron grid, then OCC's fix
            for q in multi(shapely.set_precision(g, 1e-4).buffer(0)).geoms:
                pr = Pos(0, 0, z0) * extrude(face(q), z1 - z0)
                if not pr.is_valid:
                    pr = pr.fix()
                if not pr.is_valid:
                    raise ValueError(f"invalid prism at {g.representative_point()} z={z0}..{z1}")
                out.append(pr)
            continue
        out.append(pr)
    return out
