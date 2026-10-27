import pytest
from build123d import Align, Box, Pos

from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import cross_frame, fit_test


def test_cross_frame_printable_and_slot_width():
    cf = cross_frame.make(P, 40.0)
    assert printable_problems(cf) == []
    w, sw, h = cross_frame.width(P), cross_frame.slot_w(P), cross_frame.height(P, 40)

    def material_at(z_below_top):
        x0 = -w / 2 - cross_frame.y_min(P)  # body starts here; the wire finger is to its left
        probe = Pos(x0, h - z_below_top, 0) * Box(w, 0.5, P.cf_t, align=(Align.MIN, Align.MIN, Align.MIN))
        return (cf & probe).volume / (0.5 * P.cf_t)

    assert material_at(1.0) == pytest.approx(w - 2 * sw, abs=0.01)  # above the window: only the slots
    window = P.rail_ctc - sw - 2 * P.cf_border
    assert material_at(20.0) == pytest.approx(w - 2 * sw - window, abs=0.01)


def test_shallow_cross_frame_skips_window():
    assert printable_problems(cross_frame.make(P, 8.0)) == []


def test_wire_finger_cradle():
    """Finger reaches the flange-face line; cradle floor at bus_floor; lip at the wall end."""
    cf = cross_frame.make(P, 40.0)
    ymin = cross_frame.y_min(P)
    assert ymin == pytest.approx(-(P.track_offset - P.flange_t))
    h = cross_frame.height(P, 40.0)

    def solid(y, z):  # 0.4 mm probe at run-frame (y, z) on the printed part
        probe = Pos(y - ymin - 0.2, h + z - 0.2, 0) * Box(0.4, 0.4, P.cf_t, align=(Align.MIN, Align.MIN, Align.MIN))
        return (cf & probe).volume > 1e-6

    assert solid(-20, P.bus_floor - 1)  # finger under the wires
    assert not solid(-20, P.bus_floor + 1)  # cradle open above
    assert solid(ymin + 0.5, P.bus_floor + 2)  # wall-end lip


def test_slots_grip_the_panels():
    """The first bay's cross-frames fell off the panels at the slide fit (2026-10-26) and a 0.0 clip held but not
    tightly: the slots press onto the panels (the second clip coupon's middle variant), walls stay cf_wall thick."""
    assert cross_frame.slot_w(P) == pytest.approx(P.panel_t + P.fit_cf)
    assert P.fit_cf < 0  # narrower than the panel
    assert P.fit_cf == fit_test.CF_FITS[1]
    assert cross_frame.width(P) == pytest.approx(P.rail_ctc + cross_frame.slot_w(P) + 2 * P.cf_wall)
