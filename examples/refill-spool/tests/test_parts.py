"""Test first: both halves print flat with no supports and have the sizes asked for, derived from params."""
import pytest

from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
import math

from build123d import Box, Pos, Rot

from probes import radial, radial_z, tangential_gap
from refill_spool.params import P
from refill_spool.parts import barrel_half, cap, center, ring

C = center(P)
BORE = P.bore_d / 2
R_OUT = P.barrel_d / 2
LOW = P.flange_t / 2
PLAIN_GAP = 360 / P.spokes  # between spokes 1 and 2: no strap track (straps are 0.5, 2.5, 4.5 steps round)


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


@pytest.mark.parametrize("make", [barrel_half, cap])
def test_no_bridges(make):
    assert downward_faces(make(P)) == []


def test_barrel_half_flange_is_solid_out_to_the_barrel_then_rim(barrel):
    """The barrel stands on a solid floor all round, not just where the spokes cross it."""
    for a in range(0, 360, 5):
        if min(abs((a - s + 180) % 360 - 180) for s in P.strap_angles()) < 15:
            continue  # strap tracks, below
        assert radial(barrel, C, a + 2.5, LOW, r0=BORE + 0.5, r1=R_OUT) == [pytest.approx(
            (BORE + 0.5, R_OUT), abs=0.02)], a
    assert radial(barrel, C, PLAIN_GAP / 2 + PLAIN_GAP, LOW) == [
        pytest.approx((BORE, R_OUT), abs=0.02),
        pytest.approx((P.rim_in, P.rim_d / 2), abs=0.02)]


@pytest.mark.parametrize("angle", P.strap_angles())
def test_strap_track_is_a_groove_the_barrels_full_length(barrel, angle):
    """A strap pushed in at the top can only come out at the bottom: the track has a wall behind it the whole way
    down (the barrel isn't slotted through), and opens out through the flange under it."""
    for z in (LOW, P.barrel_top / 2, P.barrel_top - 0.1):
        pieces = radial(barrel, C, angle, z, r0=BORE + P.bore_wall + 0.5, r1=P.rim_in - 0.5)
        assert pieces[-1][1] == pytest.approx(P.track_floor, abs=0.02), (z, pieces)
    behind = radial_z(barrel, C, angle, (P.nut_root + P.track_floor) / 2)
    assert behind == [pytest.approx((0, P.barrel_top), abs=1e-3)]
    assert tangential_gap(barrel, C, angle, (P.track_floor + R_OUT) / 2, P.barrel_top / 2) == pytest.approx(
        P.strap_w, abs=0.05)


def test_barrel_is_one_tube_with_the_thread_unbroken(barrel):
    """No through-slots: the barrel above the floor is one piece, and the nut ridge runs all round."""
    above = barrel & (Pos(*C, LOW + P.flange_t) * ring(P.nut_root - P.thread_depth - 0.5, R_OUT + 1, P.barrel_top))
    assert len(above.solids()) == 1


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


def test_core_key_on_the_barrel_at_the_flange(barrel):
    """A key on the barrel's outside, standing on the flange: key_len up the barrel, key_h out, key_w wide. It pokes
    into a notch in the refill's cardboard core so the coil turns with the spool."""
    z = P.flange_t + P.key_len / 2
    assert radial(barrel, C, P.key_angle, z)[-1] == pytest.approx((P.nut_root, R_OUT + P.key_h), abs=0.02)
    assert radial(barrel, C, P.key_angle, P.flange_t + P.key_len + 0.1)[-1] == pytest.approx((P.nut_root, R_OUT),
                                                                                             abs=0.02)
    assert key_width(barrel, z) == pytest.approx(P.key_w, abs=0.02)


def key_width(part, z):
    a = math.radians(P.key_angle)
    r = R_OUT + P.key_h / 2
    bar = Pos(C[0] + r * math.cos(a), C[1] + r * math.sin(a), z) * Rot(0, 0, P.key_angle) * Box(0.1, 20, 0.1)
    (piece,) = (part & bar).solids()
    return max(abs(piece.bounding_box().size.X), abs(piece.bounding_box().size.Y))


def test_bore_is_plain(barrel):
    """No notch or ring in the bore: just the tube."""
    for z in (LOW, P.flange_t + 2, P.barrel_top / 2):
        assert radial(barrel, C, P.key_angle + 30, z)[0][0] == pytest.approx(BORE, abs=0.02)


def test_cap_flange_spigot_and_lip(capp):
    """The cap's flange is solid from the bore out to the lip, so the bore ring isn't hung on the spokes."""
    lip_out = P.barrel_d / 2 + P.lip_clear + P.lip_t
    assert radial(capp, C, PLAIN_GAP * 1.5, LOW) == [
        pytest.approx((BORE, lip_out), abs=0.02),
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
