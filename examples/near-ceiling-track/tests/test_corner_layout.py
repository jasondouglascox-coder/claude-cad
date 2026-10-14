import math

import pytest

from hotrain import corner_layout as C
from hotrain.params import INCH, P


def test_radius_and_span_fill_the_alcove_exactly():
    assert P.curve_r == pytest.approx(550.3, abs=0.2)
    assert P.bow_span == pytest.approx(172.2, abs=0.2)
    b = C.bridge_corner()
    last = C.portals(P, b)[-1]
    assert last.y + P.track_offset == pytest.approx(P.alcove_w)  # P9 lands on the bump-out face


@pytest.mark.parametrize("corner", [C.inside_corner(), C.bridge_corner()])
def test_portals_lie_on_track_and_spans_are_equal(corner):
    ps = C.portals(P, corner)
    assert len(ps) == corner.n_in + P.curve_spans + corner.n_out + 1
    for a, b in zip(ps, ps[1:]):
        assert math.dist((a.x, a.y), (b.x, b.y)) == pytest.approx(P.bow_span, abs=1e-6)


def test_inside_corner_supports_are_near_walls():
    c = C.inside_corner()
    ps = C.portals(P, c)
    assert C.wall_offset(P, c, ps[0]) == pytest.approx(P.track_offset)
    assert C.wall_offset(P, c, ps[-1]) == pytest.approx(P.track_offset)
    for i, _ in c.deep:
        assert C.wall_offset(P, c, ps[i]) == pytest.approx(149.6, abs=0.5)  # ~5.9"


def test_rods_fit_six_foot_stock():
    for c in (C.inside_corner(), C.bridge_corner()):
        for side in (1, -1):
            assert C.rod_length(P, c, side) + 2 * P.bracket_t < 6 * 12 * INCH


def test_chord_stray_within_frame_clearance():
    assert C.chord_sagitta(P) == pytest.approx(6.7, abs=0.2)
