import pytest

from hotrain.params import INCH, P


def test_derived_dimensions():
    assert P.rail_ctc == pytest.approx(17.7)
    assert P.rail_ys == pytest.approx((-8.85, 8.85))
    assert P.groove_w == pytest.approx(2.4)
    assert P.rail_top == pytest.approx(P.tie_h + P.tie_plate_h + P.rail_height)
    assert round(P.tie_h / 0.2, 6) == round(P.tie_h / 0.2)  # color seam on a layer boundary
    assert P.bracket_depth == pytest.approx(3 * INCH + 4)
    assert P.bed_usable == pytest.approx(251)


def test_bay_limits_fit_the_bed():
    assert P.max_bay_len / 2 <= P.bed_usable
    assert P.min_bay_len < P.bay_len < P.max_bay_len
