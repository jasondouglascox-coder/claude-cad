"""Portal bracket (rodless inside corners): at each end of the curve the floor beam crosses the track square to the
wall, so beam and bracket are one part in that plane. The seat beam on top (the spans' frame ends and end ties sit
on it, the bus lies on its top), a plate under it braced back to the wall flange, its screws at the deep
brackets' heights."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import poly, rect
from hotrain.params import P, Params
from hotrain.parts import bracket, deep_bracket, floor_beam



def depth(p: Params) -> float:
    """Flange height below the beam top: down to the deep brackets' bottoms."""
    return deep_bracket.DEPTH - floor_beam.bottom(p)


def screw_lines(p: Params) -> tuple:
    """Screw centers below the beam top: at the deep brackets' heights, so every corner bracket shares the marks."""
    return tuple(s - floor_beam.bottom(p) for s in deep_bracket.SCREWS)


def _w(p: Params, u: float) -> float:
    """Out from the wall, for u left of the track (toward the room)."""
    return u + p.track_offset


def beam(p: Params) -> Sketch:
    """(w, h): the seat beam's profile, w out from the wall, h up from the bracket's bottom: over the flange to just
    short of the wall, the bus on its top between the frames and the wall-end lip."""
    return Pos(p.track_offset, depth(p)) * floor_beam.profile(p, rods=False)


def plate(p: Params) -> Sketch:
    """(w, h): the bracket plate under the beam: a column on the flange, a knee brace up to the beam, a gusset."""
    f, m, d = p.flange_t, p.bracket_member, depth(p)
    end = _w(p, floor_beam.half_len(p))
    bound = rect(0, end, 0, d)
    brace = deep_bracket._strut((f, 12.0), (0.6 * end, d - m / 2), deep_bracket.BRACE_W, 4.0) & bound
    gusset = poly((f - 1, 2), (f - 1, 30), (f + 16, 12))
    return Sketch() + [rect(0, f, 0, d), brace, gusset]


def make(p: Params = P) -> Part:
    """Print orientation: the beam's face and the plate flat on the bed (the beam floor_beam.thickness tall, the
    plate bracket_t), the flange standing along the wall edge."""
    return bracket.flanged(p, plate(p), depth(p), screw_lines(p)) + extrude(beam(p), floor_beam.thickness(p, False))


def place(p: Params, x_plane: float) -> Location:
    """Wall A frame: wall at y = -track_offset, the beam centered on the portal at x = x_plane, its top at the tie
    underside."""
    return (Pos(x_plane, 0, -depth(p)) * Rot(0, 0, 90) * Rot(90, 0, 0)
            * Pos(-p.track_offset, 0, -floor_beam.thickness(p, False) / 2))
