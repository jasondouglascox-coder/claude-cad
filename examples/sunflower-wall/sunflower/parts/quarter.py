"""A quarter of a petal ring (back or front): a 90-degree hub wedge plus its petals, printed flat on its back.

Petals arch: the top is a loft of cross sections, high along the midrib and `drop` lower at the edges, following the
ring's midrib profile along the length. Pins pass through slots in the hub; the back quarter also has the head
recess for each pin and a keyhole for hanging.
"""
import math
from functools import lru_cache

from build123d import (Align, Box, Compound, Cylinder, Face, Location, Part, Pos, Rot, SlotCenterToCenter, Wire, extrude,
                       loft)

from cadkit.shapes import poly
from sunflower import layout
from sunflower.params import Params

SECTIONS = 32  # loft stations along a petal
CROSS = 96  # points across each section's top: enough for the veins
BIG = 400.0


def ring(p: Params, layer: str):
    return p.back if layer == "back" else p.front


def thickness(p: Params, layer: str) -> float:
    return p.back_t if layer == "back" else p.front_t


def base_z(p: Params, layer: str) -> float:
    return 0.0 if layer == "back" else p.back_t


def outline(rg, n: int = 60):
    up = [(rg.r0 + (rg.r1 - rg.r0) * i / n, layout.half_width(rg, rg.r0 + (rg.r1 - rg.r0) * i / n))
          for i in range(n + 1)]
    return poly(*(up + [(x, -y) for x, y in reversed(up[1:-1])]))


def _lofted(p: Params, layer: str, dz: float = 0.0) -> Part:
    """The petal's arched, veined body inside its outline, with the top lowered by dz."""
    rg = ring(p, layer)
    length = rg.r1 - rg.r0
    secs = []
    for i in range(SECTIONS):
        r = rg.r0 - 1 + (length + 5) * i / (SECTIONS - 1)
        hw = max(layout.half_width(rg, r), 0.5)
        span = hw * 1.1 + 1.0  # section a bit wider than the petal; the outline trims it
        ys = [-span + 2 * span * j / CROSS for j in range(CROSS + 1)]
        top = [(r, y, max(layout.petal_top(p, rg, r, y, hw) - dz, 0.2)) for y in ys]
        # straight segments, not a spline: a spline through the vein points smooths the grooves away
        secs.append(Face(Wire.make_polygon([(r, -span, -1), (r, span, -1)] + top[::-1], close=True)))
    return Part((loft(secs) & extrude(outline(rg), 30)).solids())


@lru_cache
def petal(p: Params, layer: str) -> Part:
    """One petal along +X in its ring's frame (flat back at z = 0)."""
    return Part((_lofted(p, layer) + extrude(outline(ring(p, layer)), p.petal_min)).solids())


def _bead_strip(p: Params, k: int, n: int = 40):
    """Footprint of the bead down valley k: on the valley line, layout.bead_width wide."""
    r0, r1 = p.bead_r
    u = layout.valley_u(p, k)
    left, right = [], []
    for i in range(n + 1):
        r = r0 + (r1 - r0) * i / n
        y, w = u * layout.half_width(p.front, r), layout.bead_width(p, r)
        left.append((r, y + w / 2))
        right.append((r, y - w / 2))
    return poly(*(left + right[::-1]))


@lru_cache
def beads(p: Params) -> Part:
    """One front petal's orange beads (petal frame): the top bead_t of the petal along each middle valley."""
    skin = Part((petal(p, "front") - _lofted(p, "front", p.bead_t)).solids())
    return Part([s for k in p.bead_valleys for s in (skin & extrude(_bead_strip(p, k), 30)).solids()])


def _wedge(a0: float, gap: float):
    """90-degree wedge from a0, each edge pulled in by gap / 2."""
    k = gap / 2 / math.sin(math.radians(45))
    m = math.radians(a0 + 45)
    c = (k * math.cos(m), k * math.sin(m))
    u = lambda a: (math.cos(math.radians(a)), math.sin(math.radians(a)))
    return poly(c, (c[0] + BIG * u(a0)[0], c[1] + BIG * u(a0)[1]), (2 * BIG * u(a0 + 45)[0], 2 * BIG * u(a0 + 45)[1]),
                (c[0] + BIG * u(a0 + 90)[0], c[1] + BIG * u(a0 + 90)[1]))


def _radial_box(a: float, r: float, radial: float, tangential: float, z0: float, h: float) -> Part:
    return Rot(0, 0, a) * Pos(r, 0, z0) * Box(radial, tangential, h, align=(Align.CENTER, Align.CENTER, Align.MIN))


@lru_cache
def assembled(p: Params, layer: str) -> Part:
    """Quarter 0 in the assembly frame (z = 0 at its own flat back)."""
    layout.validate(p)
    t = thickness(p, layer)
    a0 = layout.boundaries(p, layer)[0]
    angles = layout.back_angles(p) if layer == "back" else layout.front_angles(p)
    pet = petal(p, layer)
    body = Part(Cylinder(p.hub_r, t, align=(Align.CENTER, Align.CENTER, Align.MIN)).solids())
    body = body + [Rot(0, 0, a) * pet for a in angles if layout.in_quarter(a, a0)]
    body = Part((body & extrude(_wedge(a0, p.seam_gap), 50)).solids())
    cuts = []
    for a in layout.pin_angles(p):
        if layout.in_quarter(a, a0):
            cuts.append(_radial_box(a, p.pin_r, p.pin_w + p.fit, p.pin_t + p.fit, -1, t + 2))
            if layer == "back":
                cuts.append(_radial_box(a, p.pin_r, p.pin_w + 2 * p.pin_lip + p.fit, p.pin_t + p.fit, -1,
                                        p.pin_head + 1))
    if layer == "back":
        a = a0 + 45
        r_in, r_top = p.key_r
        mid, span = (r_in + r_top) / 2, r_top - r_in
        place = Rot(0, 0, a) * Pos(mid, 0, 0)
        cuts.append(place * Pos(0, 0, -1) * extrude(SlotCenterToCenter(span, p.key_shank_w), p.key_lip + 1))
        cuts.append(place * Pos(0, 0, p.key_lip) * extrude(SlotCenterToCenter(span, p.key_head_d), t))
        cuts.append(Rot(0, 0, a) * Pos(r_in, 0, -1) *
                    Cylinder(p.key_head_d / 2, t + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return Part((body - cuts).solids())


@lru_cache
def whole(p: Params, layer: str) -> Part:
    """The whole ring in one piece: hub disk and every petal, no seams, slots or keyhole (for one-piece prints)."""
    layout.validate(p)
    angles = layout.back_angles(p) if layer == "back" else layout.front_angles(p)
    pet = petal(p, layer)
    hub = Part(Cylinder(p.hub_r, thickness(p, layer), align=(Align.CENTER, Align.CENTER, Align.MIN)).solids())
    return Part((hub + [Rot(0, 0, a) * pet for a in angles]).solids())


@lru_cache
def _shift(p: Params, layer: str) -> tuple:
    bb = (Rot(0, 0, -layout.boundaries(p, layer)[0]) * assembled(p, layer)).bounding_box()
    return (-bb.min.X, -bb.min.Y)


def _to_print(p: Params, layer: str) -> Location:
    sx, sy = _shift(p, layer)
    return Pos(sx, sy, 0) * Rot(0, 0, -layout.boundaries(p, layer)[0])


def make(p: Params, layer: str) -> Part:
    """Print orientation: flat back on the bed, the wedge in the +X +Y corner. One body, whatever its colors."""
    part = Part((_to_print(p, layer) * assembled(p, layer)).solids())
    part.label = f"{layer}_quarter"
    return part


@lru_cache
def painted(p: Params, layer: str) -> Compound:
    """make() split by color for the plate: the front quarter's yellow body with its orange beads cut out, then
    the beads (they share layers with the yellow, so the AMS swaps on each of those layers). The back is all
    yellow."""
    whole = make(p, layer)
    if layer == "back":
        return Compound(children=[whole], label=whole.label)
    a0 = layout.boundaries(p, layer)[0]
    at = _to_print(p, layer)
    orange = Part([s for a in layout.front_angles(p) if layout.in_quarter(a, a0)
                   for s in (at * Rot(0, 0, a) * beads(p)).solids()])
    yellow = Part((whole - orange).solids())
    yellow.label, orange.label = whole.label, "front_beads"
    yellow.color, orange.color = p.color(p.slot_petals), p.color(p.slot_beads)  # colored: one two-color object
    return Compound(children=[yellow, orange], label=whole.label)


def place(p: Params, layer: str, q: int) -> Location:
    """Print frame -> quarter q in the assembly frame."""
    sx, sy = _shift(p, layer)
    a0 = layout.boundaries(p, layer)[0]
    return Pos(0, 0, base_z(p, layer)) * Rot(0, 0, a0 + 90 * q) * Pos(-sx, -sy, 0)
