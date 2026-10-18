"""The clip: prints on its profile, holds the bar, keeps out of the gantry's space, carries the rail on top."""
import pytest
from build123d import Align, Box, Plane, Pos, RectangleRounded, extrude

from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
from sharpie_colorizer.parts import clip
from sharpie_colorizer.params import P


@pytest.fixture(scope="module")
def part():
    return clip.make(P)


@pytest.fixture(scope="module")
def placed(part):
    return clip.place(P) * part


def bar(length=120.0):
    return Pos(-length / 2, 0, 0) * extrude(Plane.YZ * RectangleRounded(P.bar_w, P.bar_h, P.bar_r), length)


def test_prints_flat_watertight_unsupported(part):
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert downward_faces(part) == []
    assert overhangs(part) == []


def test_clip_holds_the_bar(placed):
    assert (placed & bar()).volume == pytest.approx(0, abs=1e-3)
    assert (Pos(0, 0, 1) * placed & bar()).volume > 0.1  # pulled up off the bar, the lips catch it


def test_centered_on_the_bar(placed):
    bb = placed.bounding_box()
    assert bb.min.X == pytest.approx(-P.clip_w / 2) and bb.max.X == pytest.approx(P.clip_w / 2)
    assert bb.min.Y == pytest.approx(-bb.max.Y)


def test_nothing_below_the_lips(placed):
    assert placed.bounding_box().min.Z >= -P.bar_h / 2 - P.clip_clear - P.clip_t - 1e-3


def test_rail_on_top_at_center(placed):
    top = P.bar_h / 2 + P.clip_clear + P.clip_t + P.rail_h
    assert placed.bounding_box().max.Z == pytest.approx(top)
    probe = Pos(-5, -20, top - 0.05) * Box(0.2, 40, 0.02, align=(Align.MIN,) * 3)  # clear of the pin hole
    (head,) = (placed & probe).solids()
    assert head.bounding_box().size.Y == pytest.approx(P.rail_head, abs=0.05)
    assert head.bounding_box().center().Y == pytest.approx(0, abs=1e-3)
