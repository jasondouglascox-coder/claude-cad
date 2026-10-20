import math

import pytest
from build123d import Vector

from cadkit.checks import open_edges, overhangs
from cadkit.shapes import thread, thread_gap

R, DEPTH, PITCH, LENGTH, CREST = 30.0, 1.4, 4.0, 8.0, 0.6


def test_external_thread_is_one_watertight_solid_with_printable_flanks():
    t = thread(R, DEPTH, PITCH, LENGTH, CREST)
    assert t.is_valid and len(t.solids()) == 1
    assert open_edges(t) == 0
    assert overhangs(t) == []  # 40° flanks print without support, inside or out


def test_ridge_spans_the_helix_and_reaches_the_crest():
    t = thread(R, DEPTH, PITCH, LENGTH, CREST, z0=2.0)
    bb = t.bounding_box()
    sunk = CREST / 2 + (DEPTH + 0.3) / math.tan(math.radians(40))  # flanks run on 0.3 mm into the wall
    assert bb.min.Z == pytest.approx(2.0 - sunk, abs=0.05)
    assert bb.max.Z == pytest.approx(2.0 + LENGTH + sunk, abs=0.05)
    assert bb.max.X == pytest.approx(R + DEPTH, abs=0.05)


def test_internal_thread_points_inward():
    t = thread(R, DEPTH, PITCH, LENGTH, CREST, inward=True)
    assert t.is_valid and len(t.solids()) == 1 and overhangs(t) == []
    assert t.is_inside(Vector(R - DEPTH + 0.1, 0, 0))
    assert not t.is_inside(Vector(R + DEPTH - 0.1, 0, 0))


def test_ridge_is_right_handed_from_z0_at_plus_x():
    """Ridge center at angle 0 is at z0, a quarter turn later a quarter pitch higher, and a half pitch is groove."""
    t = thread(R, DEPTH, PITCH, LENGTH, CREST, z0=1.0)
    mid = R + DEPTH / 2
    assert t.is_inside(Vector(mid, 0, 1.0))
    assert t.is_inside(Vector(0, mid, 1.0 + PITCH / 4))
    assert t.is_inside(Vector(mid, 0, 1.0 + PITCH))
    assert not t.is_inside(Vector(mid, 0, 1.0 + PITCH / 2))


def inside_count(solid, points):
    return sum(solid.is_inside(Vector(*q)) for q in points)


def ridge_points(t, r_min):
    """Mesh vertices on the ridge's crest and flanks (outside the wall)."""
    verts, _ = t.tessellate(0.05, 0.3)
    return [(v.X, v.Y, v.Z) for v in verts if math.hypot(v.X, v.Y) > r_min][::3]


@pytest.mark.parametrize("c", [0.3, 0.5])
def test_mating_threads_mesh_half_a_pitch_out_of_phase_with_thread_gap_play(c):
    """A nut (internal ridge on R) and a bolt with radial clearance c: half a pitch apart they mesh, shifted by
    thread_gap they still clear, a little more and they touch."""
    nut = thread(R, DEPTH, PITCH, LENGTH, CREST, inward=True)
    bolt_root = R - DEPTH - c
    gap = thread_gap(DEPTH, PITCH, CREST, c)
    assert gap > 0
    for shift, clear in ((0, True), (gap - 0.03, True), (gap + 0.1, False)):
        bolt = thread(bolt_root, DEPTH, PITCH, PITCH, CREST, z0=PITCH * 1.5 + shift)
        assert (inside_count(nut, ridge_points(bolt, bolt_root + 0.05)) == 0) == clear, shift


def test_flanks_must_fit_in_the_pitch():
    with pytest.raises(ValueError, match="pitch"):
        thread(R, 2.0, 4.0, LENGTH, crest=0.5)
