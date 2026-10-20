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


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_each_plate_light(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    total = 0.0
    for f in sorted((tmp_path / "plates").glob(f"*{s.project_suffix}")):
        report = s.slice_report(f, tmp_path / f"s_{f.name}")
        assert [r[0] for r in report["layers"]] == [(1,)]
        total += sum(report["grams"].values())
    print(f"slicer: {total:.1f} g for the pair")
    assert total <= P.max_grams
