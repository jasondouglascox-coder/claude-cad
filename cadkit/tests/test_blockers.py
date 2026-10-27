"""Support blockers: a volume, not printed, inside which the slicer generates no support (a keyhole the supports
would fill, say). And reading back what a sliced plate prints, by feature, to prove it."""
import math
import zipfile
import xml.etree.ElementTree as ET

import pytest
from build123d import Part

from cadkit import bambu, bambu3mf, gcode
from cadkit.export import write_plates
from cadkit.plates import Plate
from conftest import box

PLA4 = [("PLA", "#E8862A"), ("PLA", "#F5C518"), ("PLA", "#161616"), ("PLA", "#5A3A1E")]


def shelf() -> Part:
    """A post with a slab 20 mm out at 12 mm up: the slab's underside needs support."""
    return Part((box(100, 100, 0, 10, 10, 12) + box(100, 100, 12, 30, 10, 2)).solids())


UNDER = (112, 101, 0, 17, 8, 11.8)  # the air under the slab's overhang: where the supports go
# a blocker must take in the whole overhang: Bambu drops the overhang area inside it, and grows support from any
# strip left outside it back under the rest
BLOCK = (109, 99, 0, 23, 12, 12.6)


def test_blockers_are_written_as_support_blocker_parts_and_not_as_filament(tmp_path):
    path = tmp_path / "s.3mf"
    bambu3mf.write(path, [("shelf", [("shelf", shelf(), 2), ("shelf blocker", box(*UNDER), bambu3mf.BLOCKER)])])
    cfg = ET.fromstring(zipfile.ZipFile(path).read("Metadata/model_settings.config"))
    parts = {p.find("metadata[@key='name']").get("value"): p for p in cfg.iter("part")}
    assert parts["shelf"].get("subtype") == "normal_part"
    assert parts["shelf blocker"].get("subtype") == "support_blocker"
    assert parts["shelf blocker"].find("metadata[@key='extruder']") is None
    assert bambu3mf.read_filaments(path) == [("shelf", 2, {"shelf": 2})]  # what prints: the blocker doesn't
    assert bambu3mf.read_blockers(path) == {"shelf": ["shelf blocker"]}


def test_write_plates_attaches_each_blocker_to_its_object(tmp_path):
    items = [("a", box(10, 10, 0, 10, 10, 5)), ("shelf", shelf())]
    write_plates([Plate("pl", 1, items, blockers=[("shelf", box(*UNDER))])], tmp_path, tmp_path / "p.csv",
                 lambda name: 1)
    assert bambu3mf.read_blockers(tmp_path / "pl.3mf") == {"shelf": ["shelf blocker"]}
    assert [n for n, _, _ in bambu3mf.read_filaments(tmp_path / "pl.3mf")] == ["a", "shelf"]


def test_a_blocker_for_an_object_not_on_the_plate_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="nope"):
        write_plates([Plate("pl", 1, [("shelf", shelf())], blockers=[("nope", box(*UNDER))])], tmp_path,
                     tmp_path / "p.csv", lambda name: 1)


GCODE = """\
; Z_HEIGHT: 0.2
; FEATURE: Outer wall
G1 X0 Y0 F600
G1 X10 Y0 E1.0
G1 X10 Y5 F3000
; FEATURE: Support
G1 X20 Y0 E0.5
G3 X20 Y10 I0 J5 E0.8 ; half a circle round (20, 5)
; Z_HEIGHT: 0.4
G1 Z0.4
G1 X30 Y10 E-0.8
G1 X40 Y10 E0.3
"""


def test_gcode_extrusions_by_feature_and_layer():
    segs = gcode.extrusions(GCODE)
    assert segs[0] == (0.0, 0.0, 10.0, 0.0, 0.2, "Outer wall")  # travel moves (no E, or retracting) don't count
    support = [s for s in segs if s[5] == "Support"]
    assert support[0][:4] == (10.0, 5.0, 20.0, 0.0)
    arc = support[1:-1]  # the arc as short chords, every point on its circle, going round through x = 25
    assert len(arc) > 4 and all(abs(((x1 - 20) ** 2 + (y1 - 5) ** 2) ** 0.5 - 5) < 1e-6 for _, _, x1, y1, _, _ in arc)
    assert max(x1 for _, _, x1, _, _, _ in arc) == pytest.approx(25.0, abs=0.05)
    assert segs[-1] == (30.0, 10.0, 40.0, 10.0, 0.4, "Support")
    assert [s for s in segs if s[0] == 20 and s[2] == 30] == []


def test_gcode_centre_of_mass_weighs_each_move_by_its_plastic():
    """Where the printed part balances: each extruding move weighed by its E, supports and the like left out."""
    assert gcode.centre_of_mass(GCODE) == pytest.approx((5.0, 0.0, 0.2))  # the outer wall alone
    half = (20 + 2 * 5 / math.pi, 5.0)  # a half circle's centroid
    x = (5 * 1.0 + 15 * 0.5 + half[0] * 0.8 + 35 * 0.3) / 2.6
    y = (0 * 1.0 + 2.5 * 0.5 + half[1] * 0.8 + 10 * 0.3) / 2.6
    z = (0.2 * 2.3 + 0.4 * 0.3) / 2.6
    assert gcode.centre_of_mass(GCODE, skip=()) == pytest.approx((x, y, z), abs=2e-3)


def support_under_slab(tmp_path, blockers) -> int:
    tmp_path.mkdir()
    s = bambu3mf.write_settings(tmp_path / "s.config", PLA4, overrides={"enable_support": "1",
                                                                         "support_type": "normal(auto)"})
    write_plates([Plate("pl", 1, [("shelf", shelf())], blockers=blockers)], tmp_path, tmp_path / "p.csv",
                 lambda name: 1, settings=s)
    bambu.slice_report(tmp_path / "pl.3mf", tmp_path / "pl.sliced.3mf")
    x, y, _, dx, dy, _ = UNDER
    return sum(1 for x0, y0, x1, y1, z, f in gcode.extrusions(bambu.plate_gcode(tmp_path / "pl.sliced.3mf"))
               if f.startswith("Support") and x <= (x0 + x1) / 2 <= x + dx and y <= (y0 + y1) / 2 <= y + dy)


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_supports_the_shelf_and_a_blocker_stops_it(tmp_path):
    assert support_under_slab(tmp_path / "a", []) > 50
    assert support_under_slab(tmp_path / "b", [("shelf", box(*BLOCK))]) == 0
