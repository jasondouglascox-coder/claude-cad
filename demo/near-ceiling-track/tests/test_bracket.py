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


def slot_center_x(br, p=P):
    """Run-frame X of the screw slot centerline (pier centerline = 0)."""
    from build123d import Align, Box, Pos
    zs = [z / 10 for z in range(0, int(p.flange_w * 10))]
    empty = [z for z in zs if (br & (Pos(0, p.bracket_depth - p.screw_zs[0], z)
                                     * Box(p.flange_t, 0.5, 0.1, align=(Align.MIN, Align.MIN, Align.MIN)))).volume < 1e-9]
    return (min(empty) + max(empty) + 0.1) / 2 - p.bracket_t / 2


def test_screw_slots_centered_in_flange_tab():
    """Slots sit mid-way across the exposed tab (plate face to flange edge)."""
    tab_mid = (P.bracket_t + P.flange_w) / 2 - P.bracket_t / 2
    assert slot_center_x(bracket.make(P)) == pytest.approx(tab_mid, abs=0.1)


def test_track_close_to_wall_with_car_clearance():
    assert P.track_offset == pytest.approx(1.75 * 25.4)  # corners spec: room for the bowstring's wall-side arch
    assert P.track_offset - P.car_half_w >= 10.0  # widest HO cars still clear the wall


@pytest.mark.parametrize("offset", [1.25 * 25.4, 2.5 * 25.4])
def test_bracket_printable_at_any_wall_offset(offset):
    from dataclasses import replace
    assert printable_problems(bracket.make(replace(P, track_offset=offset))) == []


def test_short_bracket_web_is_solid():
    """Close to the wall the arm is too short to triangulate; slivers would not print."""
    from build123d import Align, Box, Pos
    yf = P.flange_t
    yd0 = P.track_offset + min(P.rail_ys) - bracket.slot_w(P) / 2 - P.deck_block_margin
    assert yd0 - yf < P.bracket_open_min
    web = Pos(yf, 0, 0) * Box(yd0 - yf, P.bracket_depth, P.bracket_t, align=(Align.MIN, Align.MIN, Align.MIN))
    notch = P.bus_notch_w * -(P.bus_floor - 1) * P.bracket_t  # the wire pass-through is the only opening
    assert (bracket.make(P) & web).volume == pytest.approx(web.volume - notch, rel=1e-6)


def test_bracket_has_wire_pass_through():
    from build123d import Align, Box, Pos
    br = bracket.make(P)
    y = -(P.track_offset - P.flange_t) + 2.0  # run frame, just in front of the flange
    hole = Pos(y + P.track_offset - 0.2, P.bracket_depth + P.bus_floor + 0.5, 0) * Box(0.4, 0.4, P.bracket_t, align=(Align.MIN, Align.MIN, Align.MIN))
    under = Pos(y + P.track_offset - 0.2, P.bracket_depth + P.bus_floor - 3, 0) * Box(0.4, 0.4, P.bracket_t, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (br & hole).volume < 1e-9
    assert (br & under).volume > 1e-6


def test_half_lap_with_the_panels():
    """Pier slots come down only half the pier depth, so the bracket keeps a solid lower half; the panels'
    pier notch goes up the other half (egg-crate joint)."""
    from hotrain.parts import bracket as B
    assert P.pier_notch == pytest.approx(P.pier_depth / 2)
    prof = B.profile(P)
    y = max(P.rail_ys)
    solid = (prof & (Pos(y, -P.pier_depth + P.pier_notch - 1) * Rectangle(0.4, 0.4))).area
    slot = (prof & (Pos(y, -P.pier_depth + P.pier_notch + 1) * Rectangle(0.4, 0.4))).area
    assert solid == pytest.approx(0.16) and slot == pytest.approx(0)
    assert P.bracket_depth - (P.pier_depth - P.pier_notch) >= 40.0  # solid block under the slots


@pytest.mark.parametrize("style", ["arch", "deck_truss"])
def test_panel_pier_notch_takes_the_bracket(style):
    from dataclasses import replace
    from hotrain.parts import arch_half
    q = replace(P, run_style=style)
    half = arch_half.make(q, 16 * INCH)  # print Y 0 = pier bottom, X 0 = pier centerline
    inside = Pos(0.5, q.pier_notch - 1.0, 0) * Box(1.0, 0.5, q.panel_t, align=(Align.MIN, Align.MIN, Align.MIN))
    above = Pos(0.5, q.pier_notch + 1.0, 0) * Box(1.0, 0.5, q.panel_t, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (half & inside).volume < 1e-6 and (half & above).volume > 0
