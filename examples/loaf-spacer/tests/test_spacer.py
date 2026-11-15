"""Test first: the spacer prints flat, one solid, and matches the pan's cross-section less the fit, from params.

Print orientation: the sheet lies on the bed; the pan's 'up' is +Y, its width is X, the sheet's thickness is Z."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.settings import settings
from loaf_spacer import build
from loaf_spacer.params import P, Params
from loaf_spacer.parts import center_x, spacer


@pytest.fixture(scope="module")
def part():
    return spacer(P)


def widths_at(part, y):
    """A thin probe across the sheet at pan height y: the solid pieces' (min X, max X), left to right."""
    probe = Pos(-50, y - 0.05, -1) * Box(500, 0.1, 10, align=(Align.MIN,) * 3)
    return sorted((b.min.X, b.max.X) for b in (s.bounding_box() for s in (part & probe).solids()))


def width_at(part, y):
    (lo, hi), = widths_at(part, y)
    return hi - lo


def test_prints_flat_one_solid_watertight_on_layers(part):
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert downward_faces(part) == []


def test_thin_sheet(part):
    bb = part.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    assert bb.max.Z == pytest.approx(P.t, abs=1e-6)


def test_bottom_width_and_straight_wall(part):
    for y in (0.1, P.wall_h / 2, P.wall_h - 0.1):
        assert width_at(part, y) == pytest.approx(P.bottom_w - 2 * P.fit, abs=0.02)


def test_slant_widens_steadily_to_the_top_width(part):
    ys = [P.wall_h + (P.slant_top_h - P.wall_h) * k / 6 for k in range(1, 6)]
    ws = [width_at(part, y) for y in ys]
    assert all(b > a for a, b in zip(ws, ws[1:]))
    mid = (P.wall_h + P.slant_top_h) / 2
    # the probe is 0.1 tall, so on the slant it reads the width at its top edge: about 0.1 wider
    assert width_at(part, mid) == pytest.approx((P.bottom_w + P.top_w) / 2 - 2 * P.fit, abs=0.15)


def test_top_width_up_past_the_rim(part):
    for y in (P.slant_top_h + 0.1, P.rim_h, P.sheet_h - P.corner_r - 0.1):
        assert width_at(part, y) == pytest.approx(P.top_w - 2 * P.fit, abs=0.02)


def test_centered_and_symmetric(part):
    (lo, hi), = widths_at(part, P.rim_h)
    assert (lo + hi) / 2 == pytest.approx(center_x(P), abs=0.02)


def test_tab_with_finger_hole(part):
    assert width_at(part, P.sheet_h + P.corner_r + 0.5) == pytest.approx(P.tab_w, abs=0.02)
    (a0, a1), (b0, b1) = widths_at(part, P.hole_center_h)
    assert b0 - a1 == pytest.approx(P.hole_d, abs=0.05)
    assert b1 - a0 == pytest.approx(P.tab_w, abs=0.02)
    assert part.bounding_box().max.Y == pytest.approx(P.height, abs=1e-3)


def test_corners_are_rounded(part):
    """The tab's top corners and the sheet's top corners don't come to a point."""
    assert width_at(part, P.height - 0.2) < P.tab_w - P.tab_r
    (lo, hi), = widths_at(part, P.sheet_h - 0.2)
    assert hi - lo < P.top_w - 2 * P.fit - P.corner_r


def test_bad_profile_is_refused():
    with pytest.raises(ValueError, match="slant_top_h"):
        Params(slant_top_h=15)


def test_build_writes_a_black_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "step" / "loaf_spacer.step").exists()
    assert (tmp_path / "render" / "front.png").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"loaf_spacer_1{s.project_suffix}")}
    assert got == {"loaf_spacer": settings().filament(P.filament_black)}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_black_only(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"loaf_spacer_1{s.project_suffix}"
    back = s.roundtrip(plate)
    assert s.same_objects(back, plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_black),)]
