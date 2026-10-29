import pytest
from build123d import Align, Box, Pos, Rectangle

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


def _open_zs(br, y, p=P):
    """Print-frame Z (along the wall) where the flange is open at height y (print Y, up from the bracket bottom)."""
    zs = [z / 10 for z in range(0, int(p.flange_w * 10))]
    return [z for z in zs if (br & (Pos(0, y - 0.05, z) * Box(p.flange_t, 0.1, 0.1, align=(Align.MIN, Align.MIN, Align.MIN)))).volume < 1e-9]


def slot_center_x(br, p=P):
    """Run-frame X of the top screw's line (pier centerline = 0): the middle of its crossbar."""
    open_ = _open_zs(br, p.bracket_depth - bracket.screw_lines(p)[0], p)
    return (min(open_) + max(open_) + 0.1) / 2 - p.bracket_t / 2


def test_screw_slots_centered_in_flange_tab():
    """Slots sit mid-way across the exposed tab (plate face to flange edge)."""
    tab_mid = (P.bracket_t + P.flange_w) / 2 - P.bracket_t / 2
    assert slot_center_x(bracket.make(P)) == pytest.approx(tab_mid, abs=0.1)


@pytest.mark.parametrize("part", ["bracket", "rod_anchor"])
def test_keyhole_ts_give_side_to_side_play(part):
    """The user, 2026-10-29: "hitting the height is easy, left to right is where I need some flex", and both screws
    can have the T. The screws go in the wall first; the bracket hangs on them through two keyholes and drops, so
    each screw rides up a stem into a crossbar it slides along (about 1/2" each way) before it's tightened. The
    screw lines stay where the ceiling gauge marks them."""
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
        entry = _open_zs(br, y - P.screw_head_d)  # the keyhole, below the bar
        assert max(entry) - min(entry) + 0.1 >= P.screw_head_d - 0.3  # the head passes through it (0.1 mm probe steps)
        stem = _open_zs(br, y - P.screw_head_d / 2 + 0.3)  # between: narrower than the head, wider than the shank
        assert P.screw_d - 0.2 <= max(stem) - min(stem) + 0.1 < P.screw_head_d
