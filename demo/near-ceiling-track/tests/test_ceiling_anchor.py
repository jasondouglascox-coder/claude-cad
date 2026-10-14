"""Ceiling cleat for the braided hanging line (bridge corner): a small horn cleat screwed to a joist.
Everything the line touches is on the room side, so it can be re-cleated after the screws are in."""
import pytest
from build123d import Align, Box, Pos

from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import ceiling_anchor as CA


def _gap(c, x: float) -> float:
    """Vertical open gap (installed height) between the base top and the horn underside at print x."""
    probe = Pos(x - 0.05, 0, P.cleat_w / 2) * Box(0.1, 20, 0.1, align=(Align.MIN, Align.MIN, Align.MIN))
    pieces = sorted((s.bounding_box() for s in (c & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 2, f"expected base and horn at x={x}"
    return pieces[1].min.Y - pieces[0].max.Y


def test_printable_on_its_side_and_low_profile():
    c = CA.make(P)
    assert printable_problems(c) == []
    bb = c.bounding_box()
    assert bb.size.Y <= 7.0  # height below the ceiling
    assert bb.size.X <= 45
    assert bb.size.Z == pytest.approx(P.cleat_w)


def test_horn_gap_tapers_into_a_jam_at_the_stem():
    c = CA.make(P)
    xc = CA.center_x(P)
    for s in (1, -1):
        near = _gap(c, xc + s * (P.cleat_stem_l / 2 + 0.5))
        tip = _gap(c, xc + s * (P.cleat_horn_l / 2 - 1.0))
        assert P.line_d < near < 1.0
        assert tip >= 1.6 and tip > near


def test_screws_outside_the_horns_with_driver_access():
    c = CA.make(P)
    for x in CA.screw_xs(P):
        assert abs(x - CA.center_x(P)) > P.cleat_horn_l / 2 + 1.5
        shaft = Pos(x - 1.5, P.cleat_base_h + 0.01, 0) * Box(3.0, 20, P.cleat_w, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (c & shaft).volume < 1e-6  # nothing above the screw head
        hole = Pos(x - 1.5, -1, P.cleat_w / 2 - 0.5) * Box(3.0, P.cleat_base_h + 2, 1.0,
                                                                                  align=(Align.MIN, Align.MIN, Align.MIN))
        assert (c & hole).volume < 1e-6  # through the base


def test_placed_against_the_ceiling():
    ceiling = P.rail_top + P.rail_top_below_ceiling
    bb = (CA.place(P, 100, 50) * CA.make(P)).bounding_box()
    assert bb.max.Z == pytest.approx(ceiling)
    assert bb.min.Z == pytest.approx(ceiling - CA.height(P))
    assert bb.min.X < 100 < bb.max.X and bb.min.Y < 50 < bb.max.Y
    assert bb.size.Y == pytest.approx(P.cleat_w)
