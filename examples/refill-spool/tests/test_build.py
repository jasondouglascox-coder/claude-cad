import pytest

from cadkit import slicers
from cadkit.settings import settings
from refill_spool import build
from refill_spool.params import P


def test_build_writes_plates_steps_and_renders(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    for f in ("render/iso.png", "render/top.png", "render/cap.png", "step/barrel_half.step", "step/cap.step", "plates.csv"):
        assert (tmp_path / f).exists(), f
    s = slicers.active()
    got = {}
    for f in sorted((tmp_path / "plates").glob(f"*{s.project_suffix}")):
        got.update((n, parts) for n, _, parts in s.read_filaments(f))
    assert set(got) == {"barrel_half", "cap"}
    assert all(set(parts.values()) == {settings().filament(P.filament)} for parts in got.values())


@pytest.mark.skipif(slicers.active().project_suffix != ".3mf", reason="Bambu project files only")
def test_view_file_shows_it_screwed_together_and_strapped(tmp_path):
    """out/view/refill_spool_assembled.3mf, for looking at, not printing: each plate one object of colored parts."""
    from cadkit.bambu3mf import read_filaments, read_plates
    build.main(["--out", str(tmp_path)])
    f = tmp_path / "view" / "refill_spool_assembled.3mf"
    assert read_plates(f) == [("screwed together", ["spool"]), ("strapping, cap off", ["strapping"])]
    parts = {name: set(p) for name, _, p in read_filaments(f)}
    assert parts == {"spool": {"barrel_half", "cap"},
                     "strapping": {"barrel_half", "coil (cut in half)", "strap 1", "strap 2", "strap 3"}}


@pytest.mark.skipif(slicers.active().project_suffix != ".3mf", reason="Bambu project files only")
def test_one_project_holds_both_plates(tmp_path):
    """out/plates/refill_spool.3mf: open it once in Bambu Studio, a plate per half."""
    from cadkit.bambu3mf import read_plates
    build.main(["--out", str(tmp_path)])
    assert read_plates(tmp_path / "plates" / "refill_spool.3mf") == [("barrel_half", ["barrel_half"]),
                                                                     ("cap", ["cap"])]


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_the_project_light(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    reports = s.slice_all(tmp_path / "plates" / f"refill_spool{s.project_suffix}", tmp_path / "sliced.3mf")
    assert len(reports) == 2
    f = settings().filament(P.filament)
    assert all([r[0] for r in rep["layers"]] == [(f,)] for rep in reports)
    total = sum(sum(rep["grams"].values()) for rep in reports)
    print(f"slicer: {total:.1f} g for the pair")
    assert total <= P.max_grams


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_keeps_the_view_files_parts_together(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    f = tmp_path / "view" / f"refill_spool_assembled{s.project_suffix}"
    back = s.roundtrip(f, tmp_path / "back.3mf")
    assert s.same_objects(back, f)
    assert s.read_filaments(back) == s.read_filaments(f)
