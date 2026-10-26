"""Wall bracket at each pier: flange on the stud, triangulated arm, deck block with pier slots and a latch."""
from build123d import (Location, Part, Plane, Pos, Rot, Sketch, SlotCenterToCenter, Box, Align,
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


def flanged(p: Params, prof: Sketch, depth: float, screw_zs: tuple) -> Part:
    """Extrude a bracket profile already shifted so the wall is at x = 0 and the bottom at y = 0,
    and add the wall flange with vertical screw slots (screw_zs measured down from the top)."""
    plate = extrude(prof, p.bracket_t)
    flange = Box(p.flange_t, depth, p.flange_w, align=(Align.MIN, Align.MIN, Align.MIN))
    zc = (p.bracket_t + p.flange_w) / 2  # centered on the exposed tab; this line goes on the stud center
    holes = [extrude(Plane.YZ * Pos(depth - z, zc) * SlotCenterToCenter(2 * p.screw_travel, p.screw_d),
                     p.flange_t) for z in screw_zs]
    return plate + flange - holes


def make(p: Params = P) -> Part:
    """Print orientation: plate flat (Z 0..bracket_t), flange standing up along the wall edge (X 0..flange_t)."""
    return flanged(p, Pos(p.track_offset, p.bracket_depth) * profile(p), p.bracket_depth, p.screw_zs)


def place(p: Params, xp: float) -> Location:
    return Pos(xp, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(-p.track_offset, -p.bracket_depth, -p.bracket_t / 2)
