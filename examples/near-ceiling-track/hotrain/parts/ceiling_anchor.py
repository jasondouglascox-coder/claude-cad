"""Ceiling cleat for the bridge corner's hanging line: a small horn cleat screwed to a joist with two #6
pan-head screws outside the horns. The braid comes up, takes a turn around the stem, figure-eights over
the horns and finishes with a locking hitch; the gap under each horn narrows toward the stem so the line
jams. Everything is on the room side, so it can be re-cleated (and the corner re-levelled) at any time.
Printed on its side: the profile is the side view, extruded cleat_w, so the horns need no supports."""
from build123d import Align, Cylinder, Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import poly, rect
from hotrain.params import P, Params


def center_x(p: Params) -> float:
    return p.cleat_base_l / 2


def screw_xs(p: Params) -> list[float]:
    return [center_x(p) - p.cleat_screw_off, center_x(p) + p.cleat_screw_off]


def height(p: Params) -> float:
    return p.cleat_top


def profile(p: Params) -> Sketch:
    """(x along the cleat, y = height below the ceiling)."""
    xc, bh, sl, hl = center_x(p), p.cleat_base_h, p.cleat_stem_l / 2, p.cleat_horn_l / 2
    y_tip, y_jam = bh + p.cleat_tip_gap, bh + p.cleat_jam
    horns = poly((xc - hl, y_tip), (xc - sl, y_jam), (xc + sl, y_jam), (xc + hl, y_tip),
                 (xc + hl, y_tip + p.cleat_horn_tip), (xc, p.cleat_top), (xc - hl, y_tip + p.cleat_horn_tip))
    return Sketch() + [rect(0, p.cleat_base_l, 0, bh), rect(xc - sl, xc + sl, bh - 0.5, y_jam + 0.5), horns]


def make(p: Params = P) -> Part:
    c = extrude(profile(p), p.cleat_w)
    for x in screw_xs(p):  # vertical (installed) holes through the base
        c -= Pos(x, p.cleat_base_h / 2, p.cleat_w / 2) * Rot(90, 0, 0) * Cylinder(p.anchor_screw_d / 2, 3 * p.cleat_base_h)
    return Part(c.solids())


def place(p: Params, x: float, y: float) -> Location:
    """Base against the ceiling, cleat along world X, centered on (x, y) where the line comes up."""
    ceiling = p.rail_top + p.rail_top_below_ceiling
    return Pos(x, y - p.cleat_w / 2, ceiling) * Rot(-90, 0, 0) * Pos(-center_x(p), 0, 0)


def line_point(p: Params, x: float, y: float) -> tuple[float, float]:
    return (x, y)
