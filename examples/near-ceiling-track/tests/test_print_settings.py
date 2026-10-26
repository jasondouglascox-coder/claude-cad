"""Slicer settings every railroad plate carries: a slow first layer, for bed adhesion (the first test
bay's long thin parts came loose at the template's 50 / 105 mm/s)."""
import json
import zipfile

import pytest

from cadkit import slicers
from hotrain import build
from hotrain.params import P

pytestmark = pytest.mark.skipif(slicers.active().name != "bambu", reason="Bambu project settings")


def _settings(path):
    return json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))


def _first_layer(cfg):
    return float(cfg["initial_layer_speed"][0]), float(cfg["initial_layer_infill_speed"][0])


def test_latch_coupon_plates_print_a_slow_first_layer(tmp_path):
    assert build.main(["latch-test", "--out", str(tmp_path)]) == 0
    d = tmp_path / "latch_test"
    for f in sorted(d.glob("*.3mf")):
        assert _first_layer(_settings(f)) == (P.first_layer_speed, P.first_layer_infill_speed), f.name


def test_wire_test_keeps_its_fine_layers_and_gets_the_slow_first_layer(tmp_path):
    assert build.main(["wire-test", "--out", str(tmp_path)]) == 0
    cfg = _settings(tmp_path / "wire_test" / "wire_curve_single.3mf")
    assert _first_layer(cfg) == (P.first_layer_speed, P.first_layer_infill_speed)
    assert float(cfg["layer_height"]) == P.wire_layer


def test_first_layer_is_slower_than_the_template():
    from cadkit import bambu3mf
    tmpl = json.loads(bambu3mf.SETTINGS.read_text())
    assert P.first_layer_speed < float(tmpl["initial_layer_speed"][0])
    assert P.first_layer_infill_speed < float(tmpl["initial_layer_infill_speed"][0])


def test_petg_first_layer_bed_is_hotter_and_the_rest_unchanged(tmp_path):
    """PETG slots: textured plate first_layer_bed_temp for the first layer only; PLA slots keep the template's."""
    from cadkit import bambu3mf
    from hotrain import build
    tmpl = json.loads(bambu3mf.SETTINGS.read_text())
    cfg = json.loads(build.print_settings(P, tmp_path / "s.json").read_text())
    for i, kind in enumerate(cfg["filament_type"]):
        first = float(cfg["textured_plate_temp_initial_layer"][i])
        assert float(cfg["textured_plate_temp"][i]) == float(tmpl["textured_plate_temp"][i])
        if kind == "PETG":
            assert first == P.first_layer_bed_temp > float(tmpl["textured_plate_temp_initial_layer"][i])
        else:
            assert first == float(tmpl["textured_plate_temp_initial_layer"][i])
