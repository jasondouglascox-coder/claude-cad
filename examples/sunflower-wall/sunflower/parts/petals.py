"""The petals: one petal of either ring, the front petals' orange beads, and each ring whole (hub disk + petals).

Petals arch: the top is a loft of cross sections, high along the midrib and lower at the edges, following the
ring's midrib profile along the length, with lengthwise vein grooves. Each petal is solid down to the bed.
"""
from functools import lru_cache

from build123d import Align, Cylinder, Face, Part, Rot, Wire, extrude, loft

from cadkit.shapes import poly
from sunflower import layout
from sunflower.params import Params

SECTIONS = 32  # loft stations along a petal
CROSS = 96  # points across each section's top: enough for the veins


def ring(p: Params, layer: str):
    return p.back if layer == "back" else p.front


def thickness(p: Params, layer: str) -> float:
    return p.back_t if layer == "back" else p.front_t


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
    """Footprint of the bead down valley k: on the valley line, layout.bead_width wide, to layout.bead_end."""
    r0, r1 = p.bead_r[0], layout.bead_end(p, k)
    u = layout.valley_u(p, k)
    left, right = [], []
    for i in range(n + 1):
        r = r0 + (r1 - r0) * i / n
        y, w = u * layout.half_width(p.front, r), layout.bead_width(p, r, k)
        left.append((r, y + w / 2))
        right.append((r, y - w / 2))
    return poly(*(left + right[::-1]))


@lru_cache
def beads(p: Params) -> Part:
    """One front petal's orange beads (petal frame): the top bead_t of the petal along each middle valley."""
    skin = Part((petal(p, "front") - _lofted(p, "front", p.bead_t)).solids())
    return Part([s for k in p.bead_valleys for s in (skin & extrude(_bead_strip(p, k), 30)).solids()])


@lru_cache
def _front_petal_cut(p: Params) -> Part:
    """A front petal with its beads cut out: cutting one petal is fast, cutting the whole flower takes an hour."""
    return Part((petal(p, "front") - beads(p)).solids())


@lru_cache
def whole(p: Params, layer: str, cut_beads: bool = False) -> Part:
    """The whole ring in one piece: hub disk and every petal. cut_beads: the front petals with their beads cut out
    (the beads print in orange)."""
    angles = layout.back_angles(p) if layer == "back" else layout.front_angles(p)
    pet = _front_petal_cut(p) if cut_beads and layer == "front" else petal(p, layer)
    hub = Part(Cylinder(p.hub_r, thickness(p, layer), align=(Align.CENTER, Align.CENTER, Align.MIN)).solids())
    return Part((hub + [Rot(0, 0, a) * pet for a in angles]).solids())
