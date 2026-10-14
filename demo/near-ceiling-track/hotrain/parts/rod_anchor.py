"""Wall bracket at each end of a corner: a standard viaduct bracket (pier slots, latch, wire pass-through)
whose deck block reaches out to hold both rod ends. Rods slide in their bores, which absorbs small
differences in wall dimensions (e.g. the alcove being up to 1/4" wide)."""
from build123d import Circle, Location, Part, Pos

from hotrain.params import P, Params
from hotrain.parts import bracket


def reach(p: Params) -> float:
    return p.rod_y + p.rod_d / 2 + p.rod_wall + 2


def make(p: Params = P) -> Part:
    prof = bracket.profile(p, yd1=reach(p))
    prof -= [Pos(y, p.rod_zc) * Circle((p.rod_d + p.fit_thread) / 2) for y in (p.rod_y, -p.rod_y)]
    return bracket.flanged(p, Pos(p.track_offset, p.bracket_depth) * prof, p.bracket_depth, p.screw_zs)


def place(p: Params, xp: float) -> Location:
    return bracket.place(p, xp)
