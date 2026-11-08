"""Floor beam under each portal between two bowstring spans. Slides onto both rods (loose bores, so it
moves along hand-bent rods). The bus lies on its top on the wall side, just outside the wall-side frames, behind
their solid band, a lip at the wall end (2026-11-07: the hooks under the beams left it in plain view). The drop
variant, used only where a ceiling cable hangs the corner, reaches past the arches and has a cable eye at each end.

Without rods (inside corners, 2026-11-07) the beam has no bores and is thicker along the track: a seat reaching
under each span's end, its frames' ends and end ties, short of where the frames' skirts and lower ledges begin."""
import math

from build123d import Circle, Location, Part, Pos, Rot, Sketch, extrude

from hotrain.corner_layout import chord_sagitta
from hotrain.joints import poly, rect
from hotrain.params import P, Params
from hotrain.span_geom import span_geom


def half_len(p: Params, drop: bool = False) -> float:
    reach = p.bow_frame_y + chord_sagitta(p) + p.bow_edge_w / 2
    if drop:
        return reach + p.fb_reach
    return min(reach + 1.0, p.track_offset - 2.5)  # must stay clear of the wall at the curve's ends


def thickness(p: Params, rods: bool = True) -> float:
    """Along the track: fb_t on rods; rodless, out under both spans' ends to just short of their frames' skirts."""
    return p.fb_t if rods else p.fb_t + 2 * (p.portal_gap + p.frame_ledge_end - p.fb_seat_room)


def bottom(p: Params) -> float:
    return p.runner_bot - p.fb_drop


def wall_end(p: Params, drop: bool = False) -> float:
    """How far the beam reaches toward the wall (u < 0): on past the bus to just short of the wall at the curve's
    ends."""
    return half_len(p, drop) if drop else p.track_offset - p.corner_bus_wall_gap


def bus_z(p: Params) -> float:
    """Center of the bus bundle lying on the beam's top."""
    return p.bus_h / 2


def bus_u(p: Params) -> float:
    """Center of the bus bundle on the wall side (u < 0; +u is toward the curve center, i.e. the room): just outside
    the wall-side frames (the curve spans' sit farthest out), behind their solid band."""
    out = p.bow_frame_y + p.bow_frame_t / 2 - span_geom(p, True).yc
    return -(out + p.corner_bus_clear + p.bus_w / 2)


def plan(p: Params, pt, u: float) -> tuple[float, float]:
    """Plan position u left of the track at portal pt, along its floor beam."""
    a = math.radians(pt.heading)
    return pt.x - u * math.sin(a), pt.y + u * math.cos(a)


def eye_u(p: Params) -> float:
    return half_len(p, drop=True) - 4


def key_u(p: Params, crossing_deg: float, rods: bool = False) -> float:
    """How far along the beam from the track its deep bracket's plate reaches, under the beam, crossing it at
    crossing_deg (the beam's heading off square to the plate): the keys sit just past it, either side."""
    a = math.radians(crossing_deg)
    return (p.bracket_t / 2 + thickness(p, rods) / 2 * math.cos(a)) / math.sin(a) + p.fit_slide


def profile(p: Params, drop: bool = False, rods: bool = True, key_deg: float | None = None) -> Sketch:
    """(u, z): u left of the track (toward the curve center), z = 0 at the tie underside. A V ridge along the top
    under the track's centre keys the decks across the track; a lip on the top at the wall end keeps the bus against
    the frames. key_deg: keys under the beam either side of a deep bracket crossing it at
    that angle."""
    u, uw, zb = half_len(p, drop), wall_end(p, drop), bottom(p)
    lip = bus_u(p) - p.bus_w / 2 - p.fit_slide
    w, h = p.fb_ridge_w / 2, p.fb_ridge_h
    body = Sketch() + [rect(-uw, u, zb, 0), rect(lip - p.finger_lip_w, lip, -1, p.corner_bus_lip_h),
                       poly((-w, -0.01), (w, -0.01), (0, h))]  # the V ridge the decks' notches sit on
    if key_deg is not None:
        k = key_u(p, key_deg, rods)
        body += [rect(k, k + p.fb_key_w, zb - p.fb_key_h, zb + 1), rect(-k - p.fb_key_w, -k, zb - p.fb_key_h, zb + 1)]
    holes = [Pos(y, p.rod_zc) * Circle((p.rod_d + p.fit_thread) / 2) for y in (p.rod_y, -p.rod_y)] if rods else []
    if drop:
        holes += [Pos(y, zb / 2) * Circle((p.cable_d + 0.5) / 2) for y in (eye_u(p), -eye_u(p))]
    return body - holes if holes else body


def make(p: Params = P, drop: bool = False, rods: bool = True, key_deg: float | None = None) -> Part:
    zb = bottom(p) - (p.fb_key_h if key_deg is not None else 0)
    return Pos(wall_end(p, drop), -zb, 0) * extrude(profile(p, drop, rods, key_deg), thickness(p, rods))


def place(p: Params, x: float, y: float, heading_deg: float, drop: bool = False, rods: bool = True,
          key_deg: float | None = None) -> Location:
    """Centered on the portal point, beam across the track, thickness along the heading."""
    zb = bottom(p) - (p.fb_key_h if key_deg is not None else 0)
    return (Pos(x, y, 0) * Rot(0, 0, heading_deg) * Rot(0, 0, 90) * Rot(90, 0, 0)
            * Pos(-wall_end(p, drop), zb, -thickness(p, rods) / 2))
