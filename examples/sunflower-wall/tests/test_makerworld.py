"""The sunflower on MakerWorld: one print profile, one sliced project (G-code and thumbnail for its plate). The
flower keeps its prime tower in the front-left corner."""
import zipfile

import pytest

from cadkit import slicers
from cadkit.bambu3mf import read_plates
from sunflower import build

SUFFIX = slicers.active().project_suffix


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_makerworld_profile_is_a_sliced_project(tmp_path):
    assert build.main(["makerworld", "--out", str(tmp_path)]) == 0
    path = tmp_path / "makerworld" / f"{build.NAME}{SUFFIX}"
    assert [n for n, _ in read_plates(path)] == [build.NAME]
    files = zipfile.ZipFile(path).namelist()
    assert "Metadata/plate_1.png" in files and "Metadata/plate_1.gcode" in files
