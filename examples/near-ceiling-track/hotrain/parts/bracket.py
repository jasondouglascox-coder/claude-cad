"""Wall bracket at each pier: flange on the stud, triangulated arm, deck block with pier slots and a latch."""
import math

from build123d import (Align, Box, Circle, Location, Part, Plane, Pos, Rot, Sketch, SlotCenterToCenter,
                       extrude)

from hotrain.joints import poly, rect
from hotrain.params import P, Params


def slot_w(p: Params) -> float:
    return p.panel_t + p.fit_pier


def slots_and_latch(p: Params, slot_bottom: float, ys: tuple) -> tuple[list, Sketch]:
    """Pier slots at each y in ys (open at the top) plus the latch on the room-side slot.
    Returns (cuts, hook). Coordinates are (y, z) with z = 0 at the tie underside."""
    sw = slot_w(p)
    cuts = [rect(y - sw / 2, y + sw / 2, slot_bottom, 1) for y in ys]
    wall = max(ys) + sw / 2  # room-side wall of the room-side slot
    relief = wall + p.latch_finger_w
    if p.latch_finger_len > 0:  # the spring slot that lets the finger flex; 0 = a rigid latch
        cuts.append(rect(relief, relief + p.latch_relief, -p.latch_finger_len, 1))
    zb = -p.latch_top - p.latch_win_h + 0.5
    e = p.latch_engage
    hook = poly((wall + 0.05, zb), (wall - e, zb), (wall - e, zb + 0.8), (wall + 0.05, zb + 0.8 + e))
    return cuts, hook


def profile(p: Params, yd1: float | None = None) -> Sketch:
    """Profile in (y, z): y from the track centerline (+ room), z = 0 at the tie underside.
    yd1 overrides how far the deck block reaches toward the room (corner rod anchors reach further)."""
    yw = -p.track_offset
    yf = yw + p.flange_t
    yd0 = min(p.rail_ys) - slot_w(p) / 2 - p.deck_block_margin
    yd1 = p.tie_l / 2 if yd1 is None else yd1
    zb, m = -p.bracket_depth, p.bracket_member
    bound = rect(yw, yd1, zb, 0)
    p0, p1 = (yf, zb), (yd0, -m)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = (dx * dx + dy * dy) ** 0.5
    nx, ny = -dy / ln * m / 2, dx / ln * m / 2
    diag = poly((p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny), (p1[0] - nx, p1[1] - ny),
                (p0[0] - nx, p0[1] - ny)) & bound
    bus = rect(yf + 0.5, yf + 0.5 + p.bus_notch_w, p.bus_floor - 1, 1)  # wire pass-through
    if yd0 - yf < p.bracket_open_min:  # too short to triangulate: solid web
        body = rect(yw, yd1, zb, 0)
        cuts, hook = slots_and_latch(p, -p.pier_depth + p.pier_notch, p.rail_ys)
        return (body - cuts - bus) + hook
    body = Sketch() + [
        rect(yw, yf, zb, 0),  # wall plate
        rect(yw, yd0, -m, 0),  # top arm
        rect(yw, yd0, zb, zb + m),  # bottom arm
        diag,
        rect(yd0, yd1, zb, 0),  # deck block
    ]
    cuts, hook = slots_and_latch(p, -p.pier_depth + p.pier_notch, p.rail_ys)
    return (body - cuts - bus) + hook


def screw_lines(p: Params) -> tuple:
    """Screw centers below the bracket top: where each screw rested at the top of the old vertical slots, so the
    ceiling gauge's marks and the rail height are unchanged."""
    return tuple(z - p.screw_travel for z in p.screw_zs)


def keyhole_path(p: Params, yt: float, extra: float = 0.0) -> list[tuple[float, float]]:
    """(print Y, print Z) of a screw's way from its keyhole into the crossbar at yt: the hole's center, then up the
    ramp's middle. The hole sits a hole's width below the crossbar, by the plate; the ramp climbs from it at 45
    degrees, its roof tangent to the hole, so every underside is 45 degrees or steeper and nothing prints in
    mid-air (a level stem left the flange over it hanging between two holes)."""
    R = p.screw_head_d / 2
    ye, ze = yt - p.screw_head_d, extra + p.bracket_t + p.flange_edge + R
    zm = ze + (R - p.screw_ramp_w / 2) * math.sqrt(2)  # the ramp's middle, where it crosses the hole's center
    return [(ye, ze), (ye, zm), (yt, zm + yt - ye)]


def _keyhole(p: Params, yt: float, extra: float) -> list:
    """The keyhole's round entry and its ramp up into the crossbar, in the flange's (Y, Z) sketch plane."""
    R, s2 = p.screw_head_d / 2, math.sqrt(2)
    (ye, ze), _, _ = keyhole_path(p, yt, extra)
    roof = lambda y: ze + R * s2 + (y - ye)  # tangent to the hole on its upper side away from the crossbar
    floor = lambda y: roof(y) - p.screw_ramp_w * s2
    ramp = poly((ye - R / s2, roof(ye - R / s2)), (yt, roof(yt)), (yt, floor(yt)), (ye, floor(ye)), (ye, ze))
    return [Pos(ye, ze) * Circle(R), ramp]


def flanged(p: Params, prof: Sketch, depth: float, lines: tuple, extra: float = 0.0) -> Part:
    """Extrude a bracket profile already shifted so the wall is at x = 0 and the bottom at y = 0, and add the wall
    flange (lines: screw centers measured down from the top). The screws go in the wall first: the bracket hangs
    on them through a keyhole each and drops, so each screw rides up a ramp into a crossbar it slides along before
    it's tightened: side-to-side play, the height set. extra runs the flange on that much farther past the plate,
    the keyholes with it."""
    plate = extrude(prof, p.bracket_t)
    flange = Box(p.flange_t, depth, p.flange_w + extra, align=(Align.MIN, Align.MIN, Align.MIN))
    r = p.screw_d / 2
    z0, z1 = extra + p.bracket_t + p.flange_edge + r, extra + p.flange_w - p.flange_edge - r  # crossbar ends
    zc = (z0 + z1) / 2  # the mark: mid-way across the exposed tab
    bar = lambda y: Pos(y, zc) * SlotCenterToCenter(z1 - z0, p.screw_d, rotation=90)
    cuts = Sketch()
    for z in lines:
        yt = depth - z
        cuts += [bar(yt)] + _keyhole(p, yt, extra)
    return plate + flange - extrude(Plane.YZ * cuts, p.flange_t)


def make(p: Params = P) -> Part:
    """Print orientation: plate flat (Z 0..bracket_t), flange standing up along the wall edge (X 0..flange_t)."""
    return flanged(p, Pos(p.track_offset, p.bracket_depth) * profile(p), p.bracket_depth, screw_lines(p))


def place(p: Params, xp: float) -> Location:
    return Pos(xp, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(-p.track_offset, -p.bracket_depth, -p.bracket_t / 2)
