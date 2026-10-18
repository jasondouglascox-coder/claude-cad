"""The build writes what the user prints: plates that open black in the slicer, STEP, and the renders."""
import pytest

from cadkit import slicers
from cadkit.settings import settings
from sharpie_colorizer import build
from sharpie_colorizer.params import P


def filaments(plate):
    s = slicers.active()
    return {n: f for n, f, _ in s.read_filaments(plate)}


def test_fit_writes_a_black_fit_test_plate(tmp_path):
    assert build.main(["fit", "--out", str(tmp_path)]) == 0
    s = slicers.active()
    got = filaments(tmp_path / "plates" / f"fit_test_1{s.project_suffix}")
    assert set(got.values()) == {settings().filament(P.filament_black)}
    assert len(got) == 2 + len(P.hooks)
    assert (tmp_path / "step" / "marker_strip.step").exists()
    assert (tmp_path / "render" / "fit_test.png").exists()


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_the_fit_test_in_black_only(tmp_path):
    build.main(["fit", "--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"fit_test_1{s.project_suffix}"
    assert s.same_objects(s.roundtrip(plate), plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_black),)]


def test_all_writes_both_plates_steps_and_renders(tmp_path):
    assert build.main(["all", "--out", str(tmp_path)]) == 0
    s = slicers.active()
    for plate, n in (("fit_test_1", 2 + len(P.hooks)), ("colorizer_1", 2)):
        got = filaments(tmp_path / "plates" / f"{plate}{s.project_suffix}")
        assert set(got.values()) == {settings().filament(P.filament_black)} and len(got) == n
    for name in ("clip", "block", "assembly"):
        assert (tmp_path / "step" / f"{name}.step").exists()
    for name in ("assembly", "section", "fit_test"):
        assert (tmp_path / "render" / f"{name}.png").exists()


def test_plates_list_the_fit_test_and_the_colorizer():
    from sharpie_colorizer.plates import plates
    got = {pl.name: sorted(n for n, _ in pl.items) for pl in plates(P)}
    assert got == {"fit_test_1": sorted(["marker_strip", "tube_strip"] + [f"clip_slice_{k + 1}" for k in range(len(P.hooks))]),
                   "colorizer_1": ["block", "clip"]}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_the_colorizer_in_black_only(tmp_path):
    build.main(["all", "--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"colorizer_1{s.project_suffix}"
    assert s.same_objects(s.roundtrip(plate), plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    # the tilted mouths' top edge leaves the last layer empty: every layer with plastic is black
    assert [r[0] for r in report["layers"] if r[0]] == [(settings().filament(P.filament_black),)]
    assert set(report["grams"]) == {settings().filament(P.filament_black)}
