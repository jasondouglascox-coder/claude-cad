"""Test first: the adapter prints flat with no supports and has the sizes asked for, derived from params."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.settings import settings
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from candle import build
from candle.params import P
from candle.parts import adapter, center


@pytest.fixture(scope="module")
def part():
    return adapter(P)


def gaps_along_x(part, z):
    """Slice a thin probe through the center along X at height z: return the solid pieces' X extents."""
    cx, cy = center(P)
    probe = Pos(cx - P.base_d, cy - 0.05, z - 0.05) * Box(2 * P.base_d, 0.1, 0.1, align=(Align.MIN,) * 3)
    return sorted(((b.min.X, b.max.X) for b in (s.bounding_box() for s in (part & probe).solids())))


def test_prints_flat_watertight_on_layers(part):
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []


def test_nothing_faces_down_above_the_bed(part):
    assert downward_faces(part) == []


def test_overall_height(part):
    bb = part.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    assert bb.max.Z == pytest.approx(P.height, abs=1e-3)


def top_at(part, r):
    """Height of the outside surface at radius r from the center (a thin vertical probe)."""
    cx, cy = center(P)
    probe = Pos(cx + r - 0.05, cy - 0.05, 0) * Box(0.1, 0.1, 2 * P.height, align=(Align.MIN,) * 3)
    return (part & probe).bounding_box().max.Z


def test_base_diameter(part):
    (lo, hi), = gaps_along_x(part, P.edge_t / 2)
    assert hi - lo == pytest.approx(P.base_d, abs=0.02)


def test_edge_is_thin(part):
    assert top_at(part, P.base_d / 2 - 0.05) == pytest.approx(P.edge_t, abs=0.1)


def test_flare_slopes_up_from_the_edge_to_the_collar(part):
    """Walking in from the edge, the outside rises the whole way and reaches flare_h at the collar."""
    r_out, r_in = P.base_d / 2 - 0.1, P.collar_d / 2 + 0.1
    rs = [r_out - (r_out - r_in) * k / 8 for k in range(9)]
    hs = [top_at(part, r) for r in rs]
    assert all(b > a for a, b in zip(hs, hs[1:]))
    assert P.edge_t < hs[0] < hs[1] and hs[-1] < P.flare_h
    assert top_at(part, P.collar_d / 2 - 0.1) == pytest.approx(P.height, abs=1e-3)


def test_candle_hole_diameter_and_wall(part):
    """Above the flare and below the chamfer: two collar walls with the candle hole between them."""
    (a0, a1), (b0, b1) = gaps_along_x(part, (P.flare_h + P.height) / 2)
    assert b0 - a1 == pytest.approx(P.candle_d, abs=0.02)
    assert b1 - a0 == pytest.approx(P.collar_d, abs=0.02)


def test_candle_sits_depth_deep_on_the_floor(part):
    """The hole is open down to the floor and no further."""
    assert len(gaps_along_x(part, P.floor_t + 0.1)) == 2
    assert len(gaps_along_x(part, P.floor_t - 0.1)) == 1
    assert P.height - P.floor_t == pytest.approx(P.depth)


def test_build_writes_a_black_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "step" / "candle_adapter.step").exists()
    assert (tmp_path / "render" / "iso.png").exists() and (tmp_path / "render" / "section.png").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"candle_adapter_1{s.project_suffix}")}
    assert got == {"candle_adapter": settings().filament(P.filament_black)}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_black_only(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"candle_adapter_1{s.project_suffix}"
    back = s.roundtrip(plate)
    assert s.same_objects(back, plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_black),)]
