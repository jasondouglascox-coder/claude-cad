"""The shared cutters and profiles: the marker fits its cavity (only the grip touches), sockets have their sizes."""
import pytest
from build123d import Align, Box, Cylinder, Pos, Rectangle

from sharpie_colorizer.joints import clip_profile, marker_cavity, marker_solid, rail_profile, tube_socket
from sharpie_colorizer.layout import cone_h, mouth_l, straight_from_tip
from sharpie_colorizer.params import P

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def rod(r, z0, z1):
    return Pos(0, 0, z0) * Cylinder(r, z1 - z0, align=UP)


@pytest.mark.parametrize("reading", ["long", "short"])
@pytest.mark.parametrize("wear", [0.0, P.wear_max])
def test_only_the_grip_touches_the_cavity(reading, wear):
    below_mouth = marker_solid(P, reading, wear) & Pos(0, 0, -50) * Box(60, 60, 50 + mouth_l(P), align=UP)
    assert (below_mouth - marker_cavity(P)).volume == pytest.approx(0, abs=1e-3)


def test_worn_marker_sits_wear_deeper_with_a_blunt_felt():
    fresh, worn = marker_solid(P, "long", with_grip=True), marker_solid(P, "long", P.wear_max, with_grip=True)
    assert fresh.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
    assert worn.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
    assert worn.bounding_box().max.Z == pytest.approx(fresh.bounding_box().max.Z - P.wear_max, abs=1e-3)


def test_marker_without_felt_starts_at_the_nose():
    assert marker_solid(P, "long", felt=False).bounding_box().min.Z == pytest.approx(P.felt_l, abs=1e-3)


def test_cavity_fit_bore_diameter_and_reach():
    cav = marker_cavity(P)
    lo, hi = straight_from_tip(P, "long"), mouth_l(P)
    assert (rod(P.marker_fit_d / 2 - 0.01, lo, hi) - cav).volume == pytest.approx(0, abs=1e-3)
    assert (rod(P.marker_fit_d / 2 + 0.1, lo, hi) - cav).volume > 0.1


def test_cavity_takes_another_fit():
    cav = marker_cavity(P, fit_d=11.4)
    lo, hi = straight_from_tip(P, "long"), mouth_l(P)
    assert (rod(11.4 / 2 - 0.01, lo, hi) - cav).volume == pytest.approx(0, abs=1e-3)


def test_tube_socket_depth_and_cone():
    s = tube_socket(P)
    assert s.bounding_box().max.Z == pytest.approx(P.tube_depth + cone_h(P))
    assert (rod(P.tube_fit_d / 2 - 0.01, 0, P.tube_depth) - s).volume == pytest.approx(0, abs=1e-3)
    assert (rod(P.tube_fit_d / 2 + 0.1, 0, P.tube_depth) - s).volume > 0.1


def test_rail_slot_is_the_rail_grown_and_peaked():
    rail, slot = rail_profile(P), rail_profile(P, P.rail_clear, peaked=True)
    assert rail.bounding_box().max.Y == pytest.approx(P.rail_h)
    assert rail.bounding_box().size.X == pytest.approx(P.rail_head)
    assert (rail - slot).area == pytest.approx(0, abs=1e-6)
    assert slot.bounding_box().max.Y > P.rail_h + P.rail_head / 2  # the 45° peak


def test_clip_profile_walls_and_lips():
    prof = clip_profile(P, P.hook)
    bb = prof.bounding_box()
    outer = P.bar_w / 2 + P.clip_clear_w + P.clip_t
    assert bb.max.X == pytest.approx(outer) and bb.min.X == pytest.approx(-outer)
    assert bb.max.Y == pytest.approx(P.bar_h / 2 + P.clip_clear + P.clip_t + P.rail_h + P.rail_grow)
    assert bb.min.Y == pytest.approx(-(P.bar_h / 2 + P.clip_clear + P.clip_t))
    # the opening between the lip tips
    probe = Pos(-30, -(P.bar_h / 2 + P.clip_clear) - 0.05) * Rectangle(60, 0.1, align=(Align.MIN, Align.CENTER))
    gaps = sorted((f.bounding_box().min.X, f.bounding_box().max.X) for f in (prof & probe).faces())
    assert gaps[1][0] - gaps[0][1] == pytest.approx(P.bar_w - 2 * P.hook, abs=0.01)
