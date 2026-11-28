"""The antlers in PRINT orientation: the plate on its back on the bed, the sheep's up along +Y, the nub pointing up
(+Z, toward the sheep's nose). Drawn in 2D with shapely (tapered strokes, unioned and rounded), then extruded."""
from build123d import Align, Box, Face, Part, Pos, Vector, Wire, chamfer, extrude
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from sheep_antlers.params import P, Params

# One antler (the right one) as centerlines in a unit box: u = 0 at the root, 1 at the beam's outer tip; v = 0 at the
# top of the head, 1 at the top tine's tip. Each stroke: control points (a Bezier) and its width at start and end.
BEAM = [(0.0, -0.08), (0.05, 0.45), (0.45, 0.70), (1.0, 0.72)]
TINES = [  # (where on the beam it starts, Bezier from there)
    (0.35, [(0.15, 0.70), (0.20, 1.0)]),
    (0.70, [(0.57, 0.84), (0.63, 0.93)]),
    (0.10, [(0.25, 0.10), (0.42, 0.28)]),  # a short brow tine, out over the ear
]


def center_x(p: Params = P) -> float:
    """Shifted so the plate starts at X = 0, like every other part."""
    return p.span / 2


def bezier(pts: list, t: float) -> tuple[float, float]:
    while len(pts) > 1:
        pts = [((1 - t) * a[0] + t * b[0], (1 - t) * a[1] + t * b[1]) for a, b in zip(pts, pts[1:])]
    return pts[0]


def stroke(pts: list, w0: float, w1: float, n: int = 40):
    """A tapered stroke along a Bezier in mm: hulls of circles from w0 wide to w1, round at both ends."""
    disks = [Point(*bezier(pts, k / n)).buffer((w0 + (w1 - w0) * k / n) / 2, quad_segs=16) for k in range(n + 1)]
    return unary_union([a.union(b).convex_hull for a, b in zip(disks, disks[1:])])


def to_mm(p: Params, uv: tuple) -> tuple[float, float]:
    r = p.tip_w / 2
    return (p.root_x + uv[0] * (p.span / 2 - r - p.root_x), p.head_top + uv[1] * (p.rise - r))


def antler(p: Params = P):
    """The right antler, in mm with X = 0 on the sheep's center line."""
    beam = [to_mm(p, q) for q in BEAM]
    parts = [stroke(beam, p.beam_w, p.tip_w)]
    for t, ctrl in TINES:
        parts.append(stroke([bezier(beam, t)] + [to_mm(p, q) for q in ctrl], p.tine_w, p.tip_w))
    return unary_union(parts)


def band(p: Params = P):
    """Behind the head: from the slot bottom up to an arc band_above over the head's top arc, rounded corners."""
    arc = Point(0, p.head_top - p.head_r).buffer(p.head_r + p.band_above, quad_segs=64)
    b = arc & box(-p.band_half, 0, p.band_half, p.height)
    return b.buffer(-2, quad_segs=16).buffer(2, quad_segs=16)


def outline(p: Params = P) -> Polygon:
    """Band plus both antlers, inside corners rounded, nothing below the slot bottom (Y = 0)."""
    right = antler(p)
    g = unary_union([band(p), right, affinity.scale(right, xfact=-1, origin=(0, 0))])
    g = g.buffer(p.smooth, quad_segs=16).buffer(-p.smooth, quad_segs=16)
    g = g & box(-p.span, 0, p.span, 2 * p.height)
    if not isinstance(g, Polygon):
        raise ValueError(f"antler outline came apart into {len(g.geoms)} pieces")
    return affinity.translate(g, center_x(p), 0)


def face(g: Polygon) -> Face:
    """Counter-clockwise outside, so the face points up and extrudes up from the bed."""
    g = orient(g, 1)
    ring = lambda r: Wire.make_polygon([Vector(x, y, 0) for x, y in list(r.coords)[:-1]], close=True)
    return Face(ring(g.exterior), [ring(i) for i in g.interiors])


def antlers(p: Params = P) -> Part:
    plate = Part(extrude(face(outline(p).simplify(0.01)), p.t).solids())
    nub = Pos(center_x(p), p.nub_fit + p.nub_h / 2, p.t) * Box(p.nub_w, p.nub_h, p.nub_depth,
                                                                align=(Align.CENTER, Align.CENTER, Align.MIN))
    nub = chamfer(nub.edges().group_by()[-1], p.nub_chamfer)
    out = Part((plate + nub).solids())
    out.label = "sheep_antlers"
    return out
