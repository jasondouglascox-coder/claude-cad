"""The antlers in PRINT orientation: the plate on its back on the bed, the sheep's up along +Y, the nub pointing up
(+Z, toward the sheep's nose). Drawn in 2D with shapely (tapered strokes, unioned and rounded), then extruded."""
from build123d import (Align, Box, BuildSketch, Face, Locations, Mode, Part, Pos, Rectangle, Vector, Wire,
                       chamfer, extrude)
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
    """Behind the head: from the slot bottom up to an arc band_h high on the center line, parallel to the head's top
    arc, rounded corners."""
    arc = Point(0, p.head_top - p.head_r).buffer(p.head_r + p.band_h - p.head_top, quad_segs=64)
    b = arc & box(-p.band_half, p.bottom, p.band_half, p.height)
    return b.buffer(-2, quad_segs=16).buffer(2, quad_segs=16)


def outline(p: Params = P) -> Polygon:
    """Band plus both antlers, inside corners rounded, nothing below the nub (p.bottom)."""
    right = antler(p)
    g = unary_union([band(p), right, affinity.scale(right, xfact=-1, origin=(0, 0))])
    g = g.buffer(p.smooth, quad_segs=16).buffer(-p.smooth, quad_segs=16)
    g = g & box(-p.span, p.bottom, p.span, 2 * p.height)
    if not isinstance(g, Polygon):
        raise ValueError(f"antler outline came apart into {len(g.geoms)} pieces")
    return affinity.translate(g, center_x(p), -p.bottom)


def face(g: Polygon) -> Face:
    """Counter-clockwise outside, so the face points up and extrudes up from the bed."""
    g = orient(g, 1)
    ring = lambda r: Wire.make_polygon([Vector(x, y, 0) for x, y in list(r.coords)[:-1]], close=True)
    return Face(ring(g.exterior), [ring(i) for i in g.interiors])


def nub(p: Params, h: float, x: float, y: float, z: float) -> Part:
    """The nub that shoves into the slot: nub_w along it, h across it (centered on y), nub_depth up from z,
    chamfered tip."""
    n = Pos(x, y, z) * Box(p.nub_w, h, p.nub_depth, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return chamfer(n.edges().group_by()[-1], p.nub_chamfer)


def antlers(p: Params = P) -> Part:
    plate = Part(extrude(face(outline(p).simplify(0.01)), p.t).solids())
    out = Part((plate + nub(p, p.nub_h, center_x(p), p.slot_h / 2 - p.bottom, p.t)).solids())
    out.label = "sheep_antlers"
    return out


def fit_tab(p: Params, i: int) -> Part:
    """Fit tab i: a tab_w x tab_h handle, tab_t thick, with a nub fit_heights[i] tall at its bottom edge (centered on
    the slot like the antlers'), and i + 1 notches in its top edge to tell them apart."""
    h = p.fit_heights[i]
    y0 = min(0.0, p.slot_h / 2 - h / 2)  # the handle reaches the bottom of the tallest nub
    with BuildSketch() as sk:
        Rectangle(p.tab_w, p.tab_h - y0, align=(Align.MIN, Align.MIN))
        n = i + 1
        pitch = 2 * p.notch_w
        xs = [p.tab_w / 2 + (k - (n - 1) / 2) * pitch for k in range(n)]
        with Locations(*[(x, p.tab_h - y0) for x in xs]):
            Rectangle(p.notch_w, p.notch_d, align=(Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
    handle = Part(extrude(sk.sketch, p.tab_t).solids())
    out = Part((handle + nub(p, h, p.tab_w / 2, p.slot_h / 2 - y0, p.tab_t)).solids())
    out.label = f"fit_tab_{i + 1}"
    return out
