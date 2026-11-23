"""Leg clip (deck truss): a U slid up from below over the bottoms of the wall-side truss's two pier legs where two
bays meet at a bracket. Its end walls hook the legs' outer ends (the batter's widest, at the bottom), its sides hold
them in line, and its middle passes under the bracket's bottom bar through a notch, so the legs can't spread."""
from build123d import Align, Box, Location, Part, Pos, Rot

from hotrain import layout as L
from hotrain.params import P, Params

A = (Align.CENTER, Align.CENTER, Align.MIN)


def leg_t(p: Params) -> float:
    """A leg's thickness: the panel plus the concrete pier's raised room face."""
    return p.panel_t + p.pier_relief


def leg_reach(p: Params) -> float:
    """A leg's outer end at its bottom, from the pier centerline: the battered face's widest."""
    return L.springing_u(p) + p.pier_batter


def make(p: Params = P) -> Part:
    """Print orientation is the installed one: floor on the bed, walls up."""
    w, gy, gx = p.leg_clip_wall, leg_t(p) + p.fit_pier, 2 * leg_reach(p) + p.fit_pier
    h = p.leg_clip_floor + p.bracket_bar + p.leg_clip_grip
    clip = Box(gx + 2 * w, gy + 2 * w, h, align=A)
    clip -= Pos(0, 0, p.leg_clip_floor) * Box(gx, gy, h, align=A)  # the legs' pocket
    clip -= Pos(0, 0, p.leg_clip_floor) * Box(p.bracket_t + p.fit_slide, gy + 2 * w + 2, h, align=A)  # the bracket
    return Pos(*half_size(p), 0) * clip


def half_size(p: Params) -> tuple[float, float]:
    """Half the clip's length and width: its centre, from its corner."""
    w = p.leg_clip_wall
    return leg_reach(p) + p.fit_pier / 2 + w, (leg_t(p) + p.fit_pier) / 2 + w


def place(p: Params, x: float) -> Location:
    """Under the bracket at pier x, its floor against the bracket's bottom bar."""
    y = min(p.rail_ys) + p.pier_relief / 2  # the legs' middle: the relief is on their room face
    hx, hy = half_size(p)
    return Pos(x - hx, y - hy, -p.bracket_depth - p.leg_clip_floor)


# ---- the end clip: one leg, where a run meets a corner's rod anchor (the user, 2026-11-23) ---------------------
def _end_x0(p: Params) -> float:
    """The end clip's leg end, from the anchor's centerline (negative: the leg's side)."""
    return -(leg_reach(p) + p.fit_pier / 2 + p.leg_clip_wall)


def make_end(p: Params = P) -> Part:
    """The leg clip cut down to one leg: its pocket on one side of the anchor, the notch the anchor's bottom bar
    passes through, and a wall on the anchor's far side that hooks it. Prints as installed, floor down; corner at the
    origin."""
    w, gy = p.leg_clip_wall, leg_t(p) + p.fit_pier
    h = p.leg_clip_floor + p.bracket_bar + p.leg_clip_grip
    x0, x1 = _end_x0(p), (p.bracket_t + p.fit_slide) / 2 + w
    pocket = leg_reach(p) + p.fit_pier / 2
    clip = Pos((x0 + x1) / 2, 0, 0) * Box(x1 - x0, gy + 2 * w, h, align=A)
    clip -= Pos(-pocket / 2, 0, p.leg_clip_floor) * Box(pocket, gy, h, align=A)  # the leg
    clip -= Pos(0, 0, p.leg_clip_floor) * Box(p.bracket_t + p.fit_slide, gy + 2 * w + 2, h, align=A)  # the anchor
    return Pos(-x0, gy / 2 + w, 0) * clip


def place_end(p: Params, x: float, side: int) -> Location:
    """Under the anchor at x, its floor against the anchor's bottom bar, the leg on the -X (side -1) or +X side."""
    y = min(p.rail_ys) + p.pier_relief / 2
    hy = (leg_t(p) + p.fit_pier) / 2 + p.leg_clip_wall
    return (Pos(x, y, -p.bracket_depth - p.leg_clip_floor) * Rot(0, 0, 0 if side < 0 else 180)
            * Pos(_end_x0(p), -hy, 0))
