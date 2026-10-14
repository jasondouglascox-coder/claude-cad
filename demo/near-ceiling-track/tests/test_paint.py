"""Painted two-color parts: one solid in CAD, face colors in the STEP, split bodies for viewers."""
import re

import pytest
from build123d import Align, Box, Color, Pos

from hotrain import paint


@pytest.fixture(scope="module")
def part():
    base = Box(10, 10, 2, align=(Align.MIN, Align.MIN, Align.MIN))
    accent = Pos(2, 2, 2) * Box(3, 3, 1, align=(Align.MIN, Align.MIN, Align.MIN))
    return paint.painted(base, Color(0.4, 0.3, 0.2), accent, Color(0.8, 0.8, 0.8)), accent


def test_one_solid_with_accent_faces(part):
    fused, accent = part
    assert len(fused.solids()) == 1
    gray = [f for f in fused.faces() if tuple(paint.face_color(f))[:3] == pytest.approx((0.8, 0.8, 0.8))]
    assert len(gray) == 5  # top + 4 sides of the accent block (its bottom is internal)


def test_step_carries_face_colors_and_is_one_part(part, tmp_path):
    fused, _ = part
    placed = Pos(100, 0, 0) * fused
    placed.label = "deck"
    path = tmp_path / "p.step"
    assert paint.export_step(placed, path)
    text = path.read_text()
    assert len(re.findall(r"MANIFOLD_SOLID_BREP", text)) == 1
    rgb = set(re.findall(r"COLOUR_RGB\('[^']*',([0-9.Ee+-]+),([0-9.Ee+-]+),([0-9.Ee+-]+)\)", text))
    vals = {tuple(round(float(v), 2) for v in t) for t in rgb}
    assert (0.8, 0.8, 0.8) in vals and (0.4, 0.3, 0.2) in vals


def test_display_split_follows_placement(part):
    fused, accent = part
    bodies = paint.display_parts(Pos(100, 0, 0) * fused)
    assert bodies is not None and len(bodies) == 2
    assert bodies[1][0].bounding_box().min.X == pytest.approx(102)
