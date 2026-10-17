"""Each kit also comes as one project file with every plate (a tab per plate in Bambu Studio): the file to share on
MakerWorld. `build makerworld` slices them, so each plate carries its G-code and thumbnail."""
import csv

import pytest

from cadkit import slicers
from cadkit.bambu3mf import read_plates
from hotrain import build
from hotrain.params import P

SUFFIX = slicers.active().project_suffix


def _sheet(path):
    with open(path, encoding="utf-8") as f:
        return [(r["plate"], int(r["quantity"])) for r in csv.DictReader(f)]


@pytest.fixture(scope="module")
def starter(tmp_path_factory):
    out = tmp_path_factory.mktemp("st")
    assert build.main(["starter", "--run-style", "deck_truss", "--out", str(out)]) == 0
    return out / "starter"


def test_starter_kit_is_one_project_with_every_plate(starter):
    plates = read_plates(starter / f"starter{SUFFIX}")
    want = [n + (f" (print {q})" if q > 1 else "") for n, q in _sheet(starter / "plates.csv")]
    assert [name for name, _ in plates] == want
    assert all(objs for _, objs in plates)


def test_wire_test_kit_is_one_project_at_fine_layers(tmp_path):
    import json
    import zipfile
    assert build.main(["wire-test", "--out", str(tmp_path)]) == 0
    path = tmp_path / "wire_test" / f"wire_test{SUFFIX}"
    assert [n for n, _ in read_plates(path)] == ["wire_curve_single", "wire_curve_corner"]
    if slicers.active().name == "bambu":
        cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
        assert float(cfg["layer_height"]) == P.wire_layer


@pytest.mark.slow
def test_makerworld_files_are_sliced_with_a_thumbnail_per_plate(tmp_path):
    import zipfile
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    assert build.main(["makerworld", "--out", str(tmp_path)]) == 0
    for kit in ("starter_deck_truss", "starter_arch", "corners_pony", "corners_bowstring", "wire_rail_test"):
        path = tmp_path / "makerworld" / f"{kit}{SUFFIX}"
        names = zipfile.ZipFile(path).namelist()
        n = len(read_plates(path))
        assert n >= 2
        for i in range(1, n + 1):
            assert f"Metadata/plate_{i}.png" in names and f"Metadata/plate_{i}.gcode" in names, (kit, i)
