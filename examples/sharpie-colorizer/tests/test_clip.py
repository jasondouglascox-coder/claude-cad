"""The clip: prints on its profile, holds the bar, keeps out of the gantry's space, carries the rail on top."""
import pytest
from build123d import Align, Box, Plane, Pos, Rectangle, RectangleRounded, extrude

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
    top = P.bar_h / 2 + P.clip_clear + P.clip_t + P.rail_h + P.rail_grow
    probe = Pos(-5, -20, top - 0.05) * Box(0.2, 40, 0.02, align=(Align.MIN,) * 3)  # clear of the pin hole
    (head,) = (placed & probe).solids()
    assert head.bounding_box().center().Y == pytest.approx(0, abs=1e-3)


def test_clip_hugs_the_bar_width(placed):
    """Reprint: 0.2 mm narrower across the bar than the first print, which was loose on it."""
    probe = Pos(-1, -30, 0) * Box(0.2, 60, 0.2, align=(Align.MIN, Align.MIN, Align.CENTER))
    walls = sorted((s.bounding_box().min.Y, s.bounding_box().max.Y) for s in (placed & probe).solids())
    assert walls[1][0] - walls[0][1] == pytest.approx(P.bar_w + 2 * P.clip_clear_w, abs=1e-3)
    assert P.clip_clear_w == pytest.approx(P.clip_clear - 0.1)


def test_rail_drawn_fat_for_a_press_fit(placed):
    """Reprint: the rail is rail_grow bigger on every side than the rail the block's slot was cut around."""
    from sharpie_colorizer.joints import rail_profile
    top = P.bar_h / 2 + P.clip_clear + P.clip_t + P.rail_h + P.rail_grow
    assert placed.bounding_box().max.Z == pytest.approx(top)
    probe = Pos(-5, -20, top - 0.05) * Box(0.2, 40, 0.02, align=(Align.MIN,) * 3)
    (head,) = (placed & probe).solids()
    grown = rail_profile(P, P.rail_grow)
    at_top = grown & Pos(0, P.rail_h + P.rail_grow - 0.04) * Rectangle(40, 0.02)
    assert head.bounding_box().size.Y == pytest.approx(at_top.bounding_box().size.X, abs=0.01)


def test_reprint_variants_numbered_by_rail_size():
    """A clip per rail_grows size, k + 1 bars on clip k, so the snug one can be picked."""
    from test_fittest import bars_on_top
    items = clip.variants(P)
    assert [n for n, _ in items] == [f"clip_rail_{k + 1}" for k in range(len(P.rail_grows))]
    assert [bars_on_top(s) for _, s in items] == [k + 1 for k in range(len(P.rail_grows))]
    for _, s in items:
        assert printable_problems(s, P.printer) == [] and open_edges(s) == 0
        assert downward_faces(s) == [] and overhangs(s) == [] and off_layer_z(s, P.printer) == []
