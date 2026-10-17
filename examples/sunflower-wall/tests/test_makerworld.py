"""The sunflower on MakerWorld: one model, two print profiles, each one sliced project with every plate (G-code and
thumbnail per plate). The 10" flower keeps its prime tower in the front-left corner."""
import zipfile

import pytest

from cadkit import slicers
from cadkit.bambu3mf import read_plates
from sunflower import build

SUFFIX = slicers.active().project_suffix


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_makerworld_profiles_are_sliced_projects(tmp_path):
    assert build.main(["makerworld", "--out", str(tmp_path)]) == 0
    want = {"sunflower_16in": ["back_quarter (print 4)", "front_quarter (print 4)", "seed_head"],
            "sunflower_10in": ["sunflower_10in"]}
    for name, plates in want.items():
        path = tmp_path / "makerworld" / f"{name}{SUFFIX}"
        assert [n for n, _ in read_plates(path)] == plates
        files = zipfile.ZipFile(path).namelist()
        for i in range(1, len(plates) + 1):
            assert f"Metadata/plate_{i}.png" in files and f"Metadata/plate_{i}.gcode" in files, (name, i)
