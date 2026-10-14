"""The back: a QR code to the site and the URL in small text, both white, inlaid in the brown body.

The back is printed against the plate, so everything here is mirrored (x -> -x) to read correctly from behind.
Dark QR modules are the brown body itself; only the white panel (minus the modules) is an inlay."""
from functools import lru_cache

import numpy as np
import segno
import shapely
from build123d import Align, Location, Plane, Sketch, Text, mirror
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from . import vec as V
from .params import P, Params


def qr_matrix(p: Params = P) -> np.ndarray:
    q = segno.make(p.qr_text, error="l", micro=False, boost_error=False)
    return np.array([[bool(v) for v in row] for row in q.matrix])


def panel_box(p: Params, hole: tuple) -> tuple[float, float, float]:
    """(center x, center y, half side) of the white panel: just below the hole's brown ring, centered."""
    n = len(qr_matrix(p))
    half = (n + 2 * p.qr_quiet) * p.qr_module / 2
    hx, hy, hr = hole
    top = hy - hr - p.hole_ring_w - p.qr_gap
    return 0.0, top - half, half


@lru_cache(maxsize=2)
def qr_shapes(p: Params, hole: tuple) -> tuple[Polygon, MultiPolygon]:
    """(white panel, dark modules) in front-view mm, mirrored so the code reads from the back."""
    mat = qr_matrix(p)
    n, s = len(mat), p.qr_module
    cx, cy, half = panel_box(p, hole)
    x0, y0 = cx - n * s / 2, cy + n * s / 2
    g = 0.02  # dark modules overlap at corners so the white between them never pinches to a point
    cells = [box(x0 + c * s - g, y0 - (r + 1) * s - g, x0 + (c + 1) * s + g, y0 - r * s + g)
             for r, row in enumerate(mat) for c, v in enumerate(row) if v]
    mods = shapely.affinity.scale(unary_union(cells), xfact=-1, origin=(0, 0))
    panel = box(cx - half, cy - half, cx + half, cy + half).buffer(-p.qr_corner).buffer(p.qr_corner, quad_segs=16)
    return panel, V.multi(mods)


def url_y(p: Params, hole: tuple, silhouette, w: float, h: float) -> float:
    """Highest text center below the panel where a w x h box sits inside the silhouette with its margin."""
    cx, cy, half = panel_box(p, hole)
    inside = silhouette.buffer(-p.text_margin)
    y = cy - half - p.text_gap - h / 2
    while y > -p.width:
        if inside.contains(box(cx - w / 2, y - h / 2, cx + w / 2, y + h / 2)):
            return y
        y -= 0.1
    raise ValueError(f"the URL ({w:.1f} x {h:.1f} mm) fits nowhere under the QR panel")


def url_sketch(p: Params, hole: tuple, silhouette) -> Sketch:
    """The URL as build123d faces, mirrored, centered under the QR panel where it fits."""
    cx, cy, half = panel_box(p, hole)
    t = Text(p.url, p.text_size, font_path=p.font, align=(Align.CENTER, Align.CENTER))
    bb = t.bounding_box()
    y = url_y(p, hole, silhouette, bb.size.X, bb.size.Y)
    t = Location((cx - bb.center().X, y - bb.center().Y, 0)) * t
    return mirror(t, Plane.YZ)


def url_polys(p: Params, hole: tuple, silhouette, tol: float = 0.02) -> MultiPolygon:
    """The URL faces as shapely polygons (tessellated), for tests and previews."""
    out = []
    for f in url_sketch(p, hole, silhouette).faces():
        v, tris = f.tessellate(tol, 0.2)
        pts = [(q.X, q.Y) for q in v]
        out.append(unary_union([Polygon([pts[a], pts[b], pts[c]]) for a, b, c in tris]).buffer(1e-4).buffer(-1e-4))
    return V.multi(unary_union(out))
