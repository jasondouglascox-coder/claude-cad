"""pencil_hole: a hole a pencil point or a nail goes right through, to mark what's under a flat jig. A throat at the
bottom sets the mark's centre; a cone above it guides the point down (both the circle jig and the railroad's ceiling
gauge use it)."""
import math

import pytest
from build123d import Box, Cylinder, Pos

from cadkit.shapes import pencil_hole


def _open(hole, r, z):
    """Is the hole open a radius r out from its axis at height z?"""
    return (hole & (Pos(r, 0, z) * Box(0.05, 0.05, 0.05))).volume > 1e-9


def test_throat_then_cone_through_the_whole_thickness():
    d, h, t, deg = 4.0, 1.2, 6.0, 30.0
    hole = pencil_hole(d, h, t, deg)
    bb = hole.bounding_box()
    assert bb.min.Z < 0 and bb.max.Z > t  # cuts clean through both faces
    for z in (0.1, h - 0.1):  # the throat: straight, d across
        assert _open(hole, d / 2 - 0.1, z) and not _open(hole, d / 2 + 0.1, z)
    top = d / 2 + (t - h) * math.tan(math.radians(deg))
    assert _open(hole, top - 0.1, t - 0.05) and not _open(hole, top + 0.2, t - 0.05)


def test_cut_from_a_plate_leaves_one_solid():
    plate = Pos(0, 0, 3) * Box(20, 20, 6.0)
    cut = plate - pencil_hole(4.0, 1.2, 6.0)
    assert len(cut.solids()) == 1
    assert cut.volume == pytest.approx(plate.volume - (plate & pencil_hole(4.0, 1.2, 6.0)).volume)
    assert (cut & Cylinder(1.9, 6.0)).volume < 1e-6  # nothing left in the throat's line
