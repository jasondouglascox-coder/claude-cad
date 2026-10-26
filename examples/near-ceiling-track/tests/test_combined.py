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
    for kit in ("free_standing_bay_deck_truss", "free_standing_bay_arch", "corners_pony", "corners_bowstring",
                "wire_rail_test"):
        path = tmp_path / "makerworld" / f"{kit}{SUFFIX}"
        names = zipfile.ZipFile(path).namelist()
        n = len(read_plates(path))
        assert n >= 2
        for i in range(1, n + 1):
            assert f"Metadata/plate_{i}.png" in names and f"Metadata/plate_{i}.gcode" in names, (kit, i)
