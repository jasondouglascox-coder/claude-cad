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
