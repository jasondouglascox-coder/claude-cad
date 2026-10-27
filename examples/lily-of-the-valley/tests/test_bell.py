"""One bell, lying along +X from its apex at the origin: a rounded shoulder, straight-ish sides, a waist and a
flared, scalloped rim whose two side lobes curl back, a hollow mouth; one solid that prints without supports, white
down to the wall."""
import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import open_edges, overhangs
from lily_of_the_valley import bell
from lily_of_the_valley.params import P

MIN = (Align.MIN, Align.MIN, Align.MIN)


@pytest.fixture(scope="module")
def b():
    return bell.local(P, 1.0)


def probe(x, y, z, d=0.4):
    return Pos(x - d / 2, y - d / 2, z - d / 2) * Box(d, d, d, align=MIN)


def test_one_watertight_solid_on_the_bed_with_no_overhang(b):
    assert b.is_valid and len(b.solids()) == 1 and open_edges(b) == 0
    assert b.bounding_box().min.Z == pytest.approx(0, abs=1e-9)
    assert overhangs(b) == []


def test_size_from_params(b):
    bb = b.bounding_box()
    L, R = P.bell_len * P.bell_r, P.bell_r
    assert bb.min.X == pytest.approx(0, abs=0.2)
    assert L < bb.max.X < L + P.lobe_push * R + 0.5  # the lobe points reach past the rim
    body = P.bell_z + R * P.bell_flat * bell.profile(np.linspace(0, 1, 200)).max()
    assert body * 0.995 < bb.max.Z <= P.bell_z + P.bell_flat * bell.rim(P, 1.0)  # the lobes rise past the body


def test_rim_flares_wider_than_the_body_and_the_side_lobes_curl_back(b):
    t = np.linspace(0, 1, 200)
    prof = bell.profile(t)
    assert prof[-1] > prof[(t > 0.4) & (t < 0.8)].max() + P.flare * 0.8  # the flare
    assert np.argmin(prof[(t > 0.6)]) > 0  # a waist before it
    rim = bell.rim(P, 1.0)
    bb = b.bounding_box()
    assert bb.max.Y > rim + P.horn[0] and bb.min.Y < -rim - P.horn[0]  # the curled side lobes stick out


def test_the_mouth_is_hollow(b):
    L, R = P.bell_len * P.bell_r, P.bell_r
    assert (b & probe(L - 0.5 * P.recess * R, 0, P.bell_z)).volume == 0
    assert (b & probe(L - P.recess * R - 1.0, 0, P.bell_z)).volume == pytest.approx(0.4 ** 3, rel=1e-4)


def test_the_curled_lobes_come_down_to_the_wall_as_rounds():
    """Domes, not a round on a post: the lobes' sections stand on the bed as half-ovals up to their old tops."""
    for horn in bell._horns(P, 1.0):
        assert overhangs(horn) == [] and horn.bounding_box().min.Z == pytest.approx(0, abs=1e-9)
        assert horn.bounding_box().max.Z == pytest.approx(P.bell_z + bell.HORN_FLAT * P.horn[0], rel=1e-3)
