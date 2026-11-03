import pytest
from build123d import Align, Box, Cylinder, Pos, Rectangle, Rot

from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import bracket, end_pier


def test_bracket_printable():
    assert printable_problems(bracket.make(P)) == []


def test_bracket_extent():
    bb = bracket.make(P).bounding_box()
    assert bb.max.X == pytest.approx(P.track_offset + P.tie_l / 2)  # wall to room-side tie end
    assert bb.max.Y == pytest.approx(P.bracket_depth)
    assert bb.max.Z == pytest.approx(P.flange_w)


def test_end_pier_printable():
    assert printable_problems(end_pier.make(P)) == []


def _open_zs(br, y, p=P, width=None):
    """Print-frame Z (along the wall) where the flange is open at height y (print Y, up from the bracket bottom)."""
    zs = [z / 10 for z in range(0, int((width or p.flange_w) * 10))]
    return [z for z in zs if (br & (Pos(0, y - 0.05, z) * Box(p.flange_t, 0.1, 0.1, align=(Align.MIN, Align.MIN, Align.MIN)))).volume < 1e-9]


def slot_center_x(br, p=P):
    """Run-frame X of the top screw's line (pier centerline = 0): the middle of its crossbar."""
    open_ = _open_zs(br, p.bracket_depth - bracket.screw_lines(p)[0], p)
    return (min(open_) + max(open_) + 0.1) / 2 - p.bracket_t / 2


def test_screw_slots_centered_in_flange_tab():
    """Slots sit mid-way across the exposed tab (plate face to flange edge)."""
    tab_mid = (P.bracket_t + P.flange_w) / 2 - P.bracket_t / 2
    assert slot_center_x(bracket.make(P)) == pytest.approx(tab_mid, abs=0.1)


def _open_at(br, y, z, d, p=P):
    """True when a d-wide peg pushed straight through the flange at (print Y y, print Z z) touches nothing."""
    peg = Pos(p.flange_t / 2, y, z) * Rot(0, 90, 0) * Cylinder(d / 2, p.flange_t)
    return (br & peg).volume < 1e-6


@pytest.mark.parametrize("part", ["bracket", "rod_anchor"])
def test_keyhole_ts_give_side_to_side_play(part):
    """The user, 2026-10-29: "hitting the height is easy, left to right is where I need some flex", and both screws
    can have the T. The screws go in the wall first; the bracket hangs on them through two keyholes and drops, so
    each screw rides up a ramp into a crossbar it slides along (about 1/2" each way) before it's tightened. The
    screw lines stay where the ceiling gauge marks them. Then: "the screw head hole needs to be bigger than 8mm, so
    maybe at least 9mm? im using regular multi purpose gold screws"."""
    from hotrain.parts import rod_anchor
    br = (bracket if part == "bracket" else rod_anchor).make(P)
    d, lines = P.bracket_depth, bracket.screw_lines(P)
    assert lines[1] - lines[0] == pytest.approx(P.screw_zs[1] - P.screw_zs[0])  # the gauge's two holes
    assert lines[0] == pytest.approx(P.screw_zs[0] - P.screw_travel)  # where each screw used to rest
    for line in lines:
        y = d - line  # print Y runs up the wall from the bracket's bottom
        bar = _open_zs(br, y)
        assert (max(bar) - min(bar) + 0.1 - P.screw_d) / 2 >= 0.5 * INCH - 0.2  # within the 0.1 mm probe steps
        assert len(_open_zs(br, y + P.screw_d / 2 + 0.3)) == 0  # solid above the bar: the bracket hangs on it
        path = bracket.keyhole_path(P, y)
        (ye, ze), (yb, zb) = path[0], path[-1]
        assert ye == pytest.approx(y - P.screw_head_d) and yb == pytest.approx(y)  # drops a hole's width
        assert P.bracket_t + P.flange_edge <= ze - P.screw_head_d / 2  # clear of the plate
        assert min(bar) <= zb <= max(bar)  # the ramp lands in the crossbar
        assert _open_at(br, ye, ze, P.screw_head_max + 0.5)  # the head passes, though holes print a bit small
        for i in range(len(path) - 1):
            (y0, z0), (y1, z1) = path[i], path[i + 1]
            for t in (k / 10 for k in range(11)):
                py, pz = y0 + t * (y1 - y0), z0 + t * (z1 - z0)
                assert _open_at(br, py, pz, P.screw_d - 0.2)  # the shank rides up the ramp
                if ((py - ye) ** 2 + (pz - ze) ** 2) ** 0.5 > P.screw_head_d / 2:
                    assert not _open_at(br, py, pz, P.screw_head_max)  # and past the hole the head can't get out


@pytest.mark.parametrize("part", ["bracket", "rod_anchor", "rod_anchor_bump_out"])
def test_keyholes_have_nothing_printing_in_mid_air(part):
    """The user, 2026-11-03, watching the plate print: "this isn't a bridge, its a free hang". The old keyhole's
    stem ran level from the head hole to the crossbar, so the flange over it started in mid-air between the two
    holes (Bambu: "floating regions"). The ramp climbs at 45 degrees from the hole's side into the crossbar."""
    from cadkit.checks import floating_islands
    from hotrain.parts import rod_anchor
    br = bracket.make(P) if part == "bracket" else rod_anchor.make(P, bump_out=part.endswith("bump_out"))
    assert floating_islands(br, P.printer) == []


def test_bump_out_anchor_keeps_its_screws_off_the_corner_bead():
    """The user, 2026-11-02: the bridge corner's anchor sits right at the bump-out's outside corner, so its screws
    landed on the bullnose's metal bead; "we can make a slightly bigger bracket. we only need to by a half inch".
    Its flange runs on bump_anchor_shift farther along the wall, away from the corner, and its keyholes move with it:
    same T, same play, same height."""
    from hotrain.parts import rod_anchor
    std, long = rod_anchor.make(P), rod_anchor.make(P, bump_out=True)
    assert printable_problems(long) == []
    assert long.bounding_box().max.Z == pytest.approx(P.flange_w + P.bump_anchor_shift)
    for line in bracket.screw_lines(P):
        y = P.bracket_depth - line
        a, b = _open_zs(std, y), _open_zs(long, y, width=P.flange_w + P.bump_anchor_shift)
        assert min(b) - min(a) == pytest.approx(P.bump_anchor_shift, abs=0.11)
        assert max(b) - max(a) == pytest.approx(P.bump_anchor_shift, abs=0.11)
