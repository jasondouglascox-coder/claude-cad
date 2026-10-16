import pytest

from hotrain.params import INCH, P


def test_derived_dimensions():
    assert P.rail_ctc == pytest.approx(P.gauge + P.rail_head_w)  # gauge is between the heads' inner faces
    assert P.rail_ys == pytest.approx((-P.rail_ctc / 2, P.rail_ctc / 2))
    assert P.groove_w == pytest.approx(P.rail_base_w + P.fit_slide)
    assert (P.rail_height, P.rail_base_w, P.rail_head_w) == pytest.approx((2.54, 2.286, 1.143))  # NMRA RP-15.1 Code 100
    assert P.rail_top == pytest.approx(P.tie_h + P.tie_plate_h + P.rail_height)
    assert round(P.tie_h / 0.2, 6) == round(P.tie_h / 0.2)  # color seam on a layer boundary
    assert P.bracket_depth == pytest.approx(3 * INCH + 4)
    assert P.bed_usable == pytest.approx(P.printer.usable)  # 251 on the A1


def test_bay_limits_fit_the_bed():
    assert P.max_bay_len / 2 <= P.bed_usable
    assert P.min_bay_len < P.bay_len < P.max_bay_len
