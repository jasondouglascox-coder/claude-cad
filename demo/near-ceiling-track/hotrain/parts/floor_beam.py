"""Floor beam under each portal between two bowstring spans. Slides onto both rods (loose bores, so it
moves along hand-bent rods) and carries a side-entry bus-wire hook. The drop variant, used only where
a ceiling cable hangs the corner, reaches past the arches and has a cable eye at each end. The bus hook is on
the wall side."""
from build123d import Circle, Location, Part, Pos, Rot, Sketch, extrude

from hotrain.corner_layout import chord_sagitta
from hotrain.joints import rect
from hotrain.params import P, Params


def half_len(p: Params, drop: bool = False) -> float:
    reach = p.bow_frame_y + chord_sagitta(p) + p.bow_edge_w / 2
    if drop:
        return reach + p.fb_reach
    return min(reach + 1.0, p.track_offset - 2.5)  # must stay clear of the wall at the curve's ends


def bottom(p: Params) -> float:
    return p.runner_bot - p.fb_drop


def bus_z(p: Params) -> float:
    """Center of the bus bundle (2.4 mm tall) resting on the hook floor."""
    return bottom(p) - p.bus_hook_drop + 1.5 + 1.2


def bus_u(p: Params) -> float:
    """Bus hook position on the wall side (u < 0; +u is toward the curve center, i.e. the room), outside
    the rod, where the straight runs' wall-side bus cradles carry the wire."""
    return -(p.rod_y + 16)


def eye_u(p: Params) -> float:
    return half_len(p, drop=True) - 4


def profile(p: Params, drop: bool = False) -> Sketch:
    """(u, z): u left of the track (toward the curve center), z = 0 at the tie underside."""
    u, zb = half_len(p, drop), bottom(p)
    body = rect(-u, u, zb, 0)
    hb = bus_u(p)
    d = p.bus_hook_drop
    hook = [rect(hb - 5, hb + 5, zb - d, zb - d + 1.5), rect(hb - 5, hb - 3.5, zb - d, zb + 0.5),
            rect(hb + 3.5, hb + 5, zb - d, zb - d + 3)]
    holes = [Pos(y, p.rod_zc) * Circle((p.rod_d + p.fit_thread) / 2) for y in (p.rod_y, -p.rod_y)]
    if drop:
        holes += [Pos(y, zb / 2) * Circle((p.cable_d + 0.5) / 2) for y in (eye_u(p), -eye_u(p))]
    return (body + hook) - holes


def make(p: Params = P, drop: bool = False) -> Part:
    u, zb = half_len(p, drop), bottom(p)
    return Pos(u, -(zb - p.bus_hook_drop), 0) * extrude(profile(p, drop), p.fb_t)


def place(p: Params, x: float, y: float, heading_deg: float, drop: bool = False) -> Location:
    """Centered on the portal point, beam across the track, thickness along the heading."""
    u, zb = half_len(p, drop), bottom(p)
    return (Pos(x, y, 0) * Rot(0, 0, heading_deg) * Rot(0, 0, 90) * Rot(90, 0, 0)
            * Pos(-u, zb - p.bus_hook_drop, -p.fb_t / 2))
