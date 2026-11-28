"""Fit tabs: one nub per height in fit_heights on a small flat handle, numbered by notches, to pick nub_h."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.settings import settings
from sheep_antlers import build
from sheep_antlers.params import P
from sheep_antlers.parts import fit_tab


@pytest.fixture(scope="module", params=range(len(P.fit_heights)))
def tab(request):
    return request.param, fit_tab(P, request.param)


def test_prints_flat_one_solid(tab):
    _, t = tab
    assert printable_problems(t, P.printer) == []
    assert open_edges(t) == 0
    assert off_layer_z(t, P.printer) == []
    assert downward_faces(t) == []


def test_nub_is_its_height(tab):
    i, t = tab
    probe = Pos(-100, -100, P.tab_t + 0.1) * Box(200, 200, P.nub_depth - P.nub_chamfer - 0.2,
                                                   align=(Align.MIN,) * 3)
    bb = (t & probe).bounding_box()
    assert bb.size.Y == pytest.approx(P.fit_heights[i], abs=0.02)
    assert bb.size.X == pytest.approx(P.nub_w, abs=0.02)
    assert t.bounding_box().max.Z == pytest.approx(P.tab_t + P.nub_depth, abs=1e-3)


def test_notches_count_the_tab(tab):
    """A probe along the top edge cuts the handle into notch-count + 1 pieces."""
    i, t = tab
    bb = t.bounding_box()
    probe = Pos(-100, bb.max.Y - P.notch_d / 2, 0.1) * Box(200, 0.1, P.tab_t - 0.2, align=(Align.MIN,) * 3)
    assert len((t & probe).solids()) == i + 2


def test_build_writes_a_fit_tab_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"fit_tabs_1{s.project_suffix}")}
    assert set(got) == {f"fit_tab_{i + 1}" for i in range(len(P.fit_heights))}
    assert set(got.values()) == {settings().filament(P.filament_brown)}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_the_tabs(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"fit_tabs_1{s.project_suffix}"
    assert s.same_objects(s.roundtrip(plate), plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_brown),)]
