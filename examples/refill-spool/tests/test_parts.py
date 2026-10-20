"""Test first: both halves print flat with no supports and have the sizes asked for, derived from params."""
import pytest

from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
from probes import radial, tangential_gap
from refill_spool.params import P
from refill_spool.parts import barrel_half, cap, center

C = center(P)
BORE = P.bore_d / 2
R_OUT = P.barrel_d / 2
LOW = P.flange_t / 2
PLAIN_GAP = 360 / P.spokes  # between spokes 1 and 2: no strap slot (straps are 0.5, 2.5, 4.5 steps round)


@pytest.fixture(scope="module")
def barrel():
    return barrel_half(P)


@pytest.fixture(scope="module")
def capp():
    return cap(P)


@pytest.mark.parametrize("make", [barrel_half, cap])
def test_prints_flat_watertight_on_layers_without_support(make):
    part = make(P)
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    bridges = {z for z, _ in downward_faces(part)}
    assert {z for z, _ in overhangs(part)} <= bridges  # nothing angled past 45°; flat bridges are tested below


def test_barrel_half_only_bridges_the_notch_roof(barrel):
    faces = downward_faces(barrel)
    assert {z for z, _ in faces} == {P.notch_depth}
    assert sum(a for _, a in faces) <= P.notch_w * (P.notch_h + 0.1)  # its inner edge follows the bore


def test_cap_has_no_bridges(capp):
    assert downward_faces(capp) == []


def test_barrel_half_flange_is_hub_barrel_rim(barrel):
    assert radial(barrel, C, PLAIN_GAP / 2 + PLAIN_GAP, LOW) == [
        pytest.approx((BORE, BORE + P.hub_wall), abs=0.02),
        pytest.approx((P.nut_root, R_OUT), abs=0.02),
        pytest.approx((P.rim_in, P.rim_d / 2), abs=0.02)]


@pytest.mark.parametrize("angle", P.strap_angles())
def test_strap_slot_runs_the_barrels_full_length(barrel, angle):
    for z in (LOW, P.barrel_top / 2, P.barrel_top - 0.1):
        pieces = radial(barrel, C, angle, z, r0=BORE + P.hub_wall + 0.5, r1=P.rim_in - 0.5)
        assert pieces == [], (z, pieces)
    assert tangential_gap(barrel, C, angle, R_OUT - P.barrel_wall / 2, P.barrel_top / 2) == pytest.approx(
        P.strap_w, abs=0.05)


def test_spokes_reach_from_hub_to_rim(barrel, capp):
    for part in (barrel, capp):
        for a in P.spoke_angles():
            pieces = radial(part, C, a + 1, LOW, r0=BORE + 0.5)
            assert len(pieces) == 1 and pieces[0][1] == pytest.approx(P.rim_d / 2, abs=0.02)


def test_barrel_height_and_outside_diameter(barrel):
    assert barrel.bounding_box().max.Z == pytest.approx(P.barrel_top, abs=1e-3)
    assert radial(barrel, C, PLAIN_GAP * 1.5, P.barrel_top / 2) == [
        pytest.approx((BORE, BORE + P.bore_wall), abs=0.02),
        pytest.approx((P.nut_root, R_OUT), abs=0.02)]


def test_nut_thread_inside_the_barrel_top(barrel):
    """Somewhere round the middle of the top band the ridge stands thread_depth in from the wall."""
    inner = min(r[0][0] for a in range(0, 360, 5) if (r := radial(barrel, C, a, P.barrel_top - P.thread_len / 2,
                                                             r0=BORE + P.bore_wall + 0.5)))
    assert inner == pytest.approx(P.nut_root - P.thread_depth, abs=0.05)


def test_ams_lite_notch(barrel):
    """Notch in the bore at the outer face: notch_depth in, notch_h into the wall, notch_w wide."""
    assert radial(barrel, C, 0, P.notch_depth / 2)[0][0] == pytest.approx(BORE + P.notch_h, abs=0.02)
    assert radial(barrel, C, 0, P.notch_depth + 0.5)[0][0] == pytest.approx(BORE, abs=0.02)
    assert tangential_gap(barrel, C, 0, BORE + P.notch_h / 2, P.notch_depth / 2) == pytest.approx(
        P.notch_w, abs=0.05)


def test_cap_flange_spigot_and_lip(capp):
    lip_out = P.barrel_d / 2 + P.lip_clear + P.lip_t
    assert radial(capp, C, PLAIN_GAP * 1.5, LOW) == [
        pytest.approx((BORE, BORE + P.cap_hub_wall), abs=0.02),
        pytest.approx((P.bolt_root - P.spigot_wall, lip_out), abs=0.02),
        pytest.approx((P.rim_in, P.rim_d / 2), abs=0.02)]
    lip = radial(capp, C, PLAIN_GAP * 1.5, P.flange_t + 0.1, r0=P.barrel_d / 2 - 0.5, r1=P.rim_in - 0.5)
    assert lip == [pytest.approx((P.barrel_d / 2 + P.lip_clear, lip_out), abs=0.02)]
    top = radial(capp, C, PLAIN_GAP * 1.5, P.flange_t + P.lip_h - 0.05, r0=P.barrel_d / 2 - 0.5, r1=P.rim_in - 0.5)
    assert top[0][0] > P.barrel_d / 2 + P.lip_clear + P.lip_chamfer / 2  # lead-in at the lip's tip
    assert capp.bounding_box().max.Z == pytest.approx(P.flange_t + P.thread_len, abs=1e-3)
    outer = max(radial(capp, C, a, P.flange_t + P.thread_len / 2)[0][1] for a in range(0, 360, 5))
    assert outer == pytest.approx(P.bolt_root + P.thread_depth, abs=0.05)


def test_overall_size_fits_the_ams():
    assert P.width <= 67.0 and P.rim_d <= 200.0
