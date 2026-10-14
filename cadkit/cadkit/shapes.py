"""2D profile helpers. Flat-printed parts are profiles extruded to a thickness, so most geometry starts here."""
from build123d import Align, Kind, Polygon, Pos, Rectangle, Sketch, offset


def poly(*pts: tuple) -> Sketch:
    """Polygon traced counter-clockwise whatever order the points come in, so it extrudes toward +Z.
    (A clockwise Polygon extrudes toward -Z and the part silently splits into several solids.)"""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    return Polygon(*(pts if area > 0 else pts[::-1]), align=None)


def rect(u0: float, u1: float, v0: float, v1: float) -> Sketch:
    """Axis-aligned rectangle from corner (u0, v0) to (u1, v1)."""
    return Pos(u0, v0) * Rectangle(u1 - u0, v1 - v0, align=(Align.MIN, Align.MIN))


def grow(s: Sketch, clearance: float) -> Sketch:
    """Grow a profile by a fit clearance, keeping sharp corners."""
    return offset(s, clearance, kind=Kind.INTERSECTION) if clearance else s


def bowtie(length: float, head: float, waist: float, clearance: float = 0.0) -> Sketch:
    """Bow-tie (butterfly) key: waist on the joint line x = 0, heads at x = ±length/2. Locks two flat parts
    edge to edge; cut the socket with clearance > 0."""
    hl, hh, hw = length / 2, head / 2, waist / 2
    return grow(poly((-hl, -hh), (0, -hw), (hl, -hh), (hl, hh), (0, hw), (-hl, hh)), clearance)


def dovetail(x: float, y: float, neck: float, head: float, length: float, clearance: float = 0.0) -> Sketch:
    """Jigsaw tab with its neck on x, widening toward +x. Joins long flat parts end to end."""
    n, h = neck / 2, head / 2
    return grow(poly((x - 0.01, y - n), (x + length, y - h), (x + length, y + h), (x - 0.01, y + n)), clearance)
