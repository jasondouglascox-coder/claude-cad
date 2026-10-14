"""Wall bracket reaching ~6" out to hold a floor beam from below, between two stops. A real knee brace:
a gusset where it leaves the flange, rising at ~30° to meet the top arm well out along it."""
import math

from build123d import Location, Part, Pos, Rot, Sketch

from hotrain.joints import poly, rect
from hotrain.params import P, Params
from hotrain.parts import bracket, floor_beam

DEPTH = 70.0
BRACE_W = 7.0
SCREWS = (12.0, DEPTH - 12.0)  # down from the top


def top(p: Params) -> float:
    return floor_beam.bottom(p)


def band(p: Params, beam_angle_deg: float) -> float:
    """Half-width of the floor beam's footprint where it crosses the bracket's thickness."""
    a = math.radians(beam_angle_deg)
    return (p.fb_t / 2) / math.sin(a) + (p.bracket_t / 2) / math.tan(a)


def _strut(a: tuple, b: tuple, w: float, ext: float) -> Sketch:
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy * w / 2, ux * w / 2
    a2, b2 = (a[0] - ux * ext, a[1] - uy * ext), (b[0] + ux * ext, b[1] + uy * ext)
    return poly((a2[0] + nx, a2[1] + ny), (b2[0] + nx, b2[1] + ny), (b2[0] - nx, b2[1] - ny), (a2[0] - nx, a2[1] - ny))


def profile(p: Params, w_beam: float, beam_angle_deg: float) -> Sketch:
    """(w, z): w out from the wall, z from the bottom; the beam crosses at w = w_beam."""
    bw = band(p, beam_angle_deg) + p.portal_gap
    end = w_beam + bw + 3 + p.deep_reach_margin
    m, f = p.bracket_member, p.flange_t
    bound = rect(0, end, 0, DEPTH)
    brace = _strut((f, 12.0), (0.6 * end, DEPTH - m / 2), BRACE_W, 4.0) & bound  # runs into flange and arm
    gusset = poly((f - 1, 2), (f - 1, 30), (f + 16, 12))
    return Sketch() + [
        rect(0, f, 0, DEPTH),  # flange web
        rect(0, end, DEPTH - m, DEPTH),  # top arm
        brace,
        gusset,
        rect(w_beam - bw - 3, w_beam - bw, DEPTH, DEPTH + 3),  # stops either side of the beam
        rect(w_beam + bw, w_beam + bw + 3, DEPTH, DEPTH + 3),
    ]


def make(p: Params, w_beam: float, beam_angle_deg: float) -> Part:
    return bracket.flanged(p, profile(p, w_beam, beam_angle_deg), DEPTH, SCREWS)


def place(p: Params, x_plane: float) -> Location:
    """Wall A frame: wall at y = -track_offset, bracket plane x = x_plane, top at the beam bottom."""
    return (Pos(x_plane, 0, top(p) - DEPTH) * Rot(0, 0, 90) * Rot(90, 0, 0)
            * Pos(-p.track_offset, 0, -p.bracket_t / 2))
