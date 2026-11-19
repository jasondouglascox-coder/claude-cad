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


def test_rivet_heads_print_slowly(tmp_path):
    """The user, 2026-11-19: rivets sometimes print rough. Each head is a loop under a millimetre round, printed at the
    outer wall's ~190 mm/s between a retract, a hop and a wipe. Every loop shorter than 2 pi rivet_loop_r slows to
    rivet_speed (Bambu's small perimeters); the rest of the print keeps its speeds."""
    import math
    cfg = json.loads(build.print_settings(P, tmp_path / "s.json").read_text())
    assert cfg["small_perimeter_speed"] == [f"{P.rivet_speed:g}"]
    assert cfg["small_perimeter_threshold"] == [f"{P.rivet_loop_r:g}"]
    assert math.pi * P.rivet_d < 2 * math.pi * P.rivet_loop_r  # a head's loop is caught
    assert P.rivet_speed < float(cfg["outer_wall_speed"][0])


def test_gray_on_the_ties_prints_slowly(tmp_path):
    """The user, 2026-11-19: the gray "nails" (spike heads) come out sloppy. Their outer loops were already slowed
    with the rivets; inside each one Bambu laid gap infill at 250 mm/s. Every gray body on a brown part (the clips
    and spike heads on the ties) gets spike_speed for everything it prints; the brown keeps the project's speeds."""
    import xml.etree.ElementTree as ET
    from build123d import Compound, Pos, Box, Align
    from cadkit import bambu3mf
    from hotrain.room import IRON, TIE_BROWN
    from hotrain.plates import Plate
    wood = Box(40, 10, P.tie_h, align=(Align.MIN,) * 3)
    steel = Pos(2, 2, P.tie_h) * Box(1.3, 0.8, P.clip_h, align=(Align.MIN,) * 3)
    wood.label, wood.color, steel.label, steel.color = "ladder_wood", TIE_BROWN, "ladder_steel", IRON
    plain = Pos(0, 20, 0) * Box(40, 10, 2, align=(Align.MIN,) * 3)
    build.write_plates([Plate("pl", 1, [("ladder", Compound(children=[wood, steel], label="ladder")),
                                        ("cross_frame", plain)])], tmp_path, tmp_path / "p.csv", p=P)
    parts = {}
    for o in ET.fromstring(zipfile.ZipFile(tmp_path / "pl.3mf").read("Metadata/model_settings.config")).iter("object"):
        for pt in o.findall("part"):
            meta = bambu3mf._meta(pt)
            name = meta.pop("name")
            parts[name] = {k: v for k, v in meta.items() if k != "extruder"}
    assert parts["ladder_wood"] == {} and parts["cross_frame"] == {}
    slow = parts["ladder_steel"]
    assert {"outer_wall_speed", "inner_wall_speed", "gap_infill_speed"} <= set(slow)
    assert all(v == f"{P.spike_speed:g}" for v in slow.values())


@pytest.mark.slow
def test_bambu_prints_a_ladders_gray_slowly(tmp_path):
    from cadkit import gcode
    from hotrain import layout as L
    from hotrain.parts import tie_ladder
    from hotrain.plates import Plate
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    bays = [16 * 25.4]
    lad = tie_ladder.make_colored(P, bays, L.segments(P, bays)[0])
    build.write_plates([Plate("lad", 1, plates_pack(lad))], tmp_path, tmp_path / "p.csv", p=P)
    s.slice_report(tmp_path / "lad.3mf", tmp_path / "s.3mf")
    g = zipfile.ZipFile(tmp_path / "s.3mf").read("Metadata/plate_1.gcode").decode()
    gray = {k: v for k, v in gcode.speeds(g, above=P.tie_h + 1e-6).items() if k != "Prime tower"}
    assert "Gap infill" in gray and "Outer wall" in gray, gray
    assert max(gray.values()) <= P.spike_speed + 0.5, gray
    assert gcode.speeds(g, above=0.3)["Inner wall"] > 2 * P.spike_speed  # the brown ties keep theirs


def plates_pack(part):
    from hotrain import plates
    return plates.pack(P, [("ladder", part)])[0]
