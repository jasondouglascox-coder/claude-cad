"""Shared 2D joint shapes. All are build123d sketches centered on the joint line."""
from build123d import Align, Kind, Polygon, Pos, Rectangle, Sketch, offset

from hotrain.params import Params


def poly(*pts: tuple) -> Sketch:
    """Polygon traced counter-clockwise whatever order the points come in, so it extrudes toward +Z."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def rect(u0: float, u1: float, v0: float, v1: float) -> Sketch:
    """Axis-aligned rectangle from corner (u0, v0) to (u1, v1)."""
    return Pos(u0, v0) * Rectangle(u1 - u0, v1 - v0, align=(Align.MIN, Align.MIN))


def butterfly(p: Params, clearance: float = 0.0) -> Sketch:
    """Bow-tie key: waist on the joint line (x=0), heads at x = ±key_len/2. clearance grows it."""
    hl, hh, hw = p.key_len / 2, p.key_head / 2, p.key_waist / 2
    key = poly((-hl, -hh), (0, -hw), (hl, -hh), (hl, hh), (0, hw), (-hl, hh))
    return offset(key, clearance, kind=Kind.INTERSECTION) if clearance else key


def jigsaw(p: Params, x: float, y: float, clearance: float = 0.0) -> Sketch:
    """Dovetail tab whose neck sits on x and widens toward +x (into the next ladder)."""
    n, h = p.jig_neck / 2, p.jig_head / 2
    tab = poly((x - 0.01, y - n), (x + p.jig_len, y - h), (x + p.jig_len, y + h), (x - 0.01, y + n))
    return offset(tab, clearance, kind=Kind.INTERSECTION) if clearance else tab
