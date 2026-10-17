"""Plates open in Bambu Studio already colored: a Bambu project 3MF with a filament per part."""
import json
import zipfile
from collections import Counter

import numpy as np
import pytest
from build123d import Pos

from cadkit import bambu, bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate
from conftest import box

FIL = {"deck_wood": 2, "deck_steel": 1}
filament = lambda name: FIL.get(name, 1)


def _write(tmp_path, items, name="pl"):
    write_plates([Plate(name, 1, items)], tmp_path, tmp_path / "p.csv", filament, colors=4, color_changes=99)
    return tmp_path / f"{name}.3mf"


def test_two_color_part_is_one_object_with_a_filament_per_part(tmp_path, two_color):
    path = _write(tmp_path, [("deck", two_color())])
    model = zipfile.ZipFile(path).read("3D/3dmodel.model").decode()
    assert '<metadata name="Application">BambuStudio-' in model  # Bambu reads part filaments only from its format
    assert model.count("<item ") == 1  # one object: the upper color can't drop onto the bed
    assert bambu3mf.read_filaments(path) == [("deck", 2, {"deck_wood": 2, "deck_steel": 1})]
    proj = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    assert proj["printer_settings_id"].startswith("Bambu Lab A1")  # without project settings the CLI crashes


def test_mesh_ids_unique_across_the_file(tmp_path, two_color):
    """Bambu keys meshes by id alone: a repeated id makes it reuse another object's mesh."""
    path = _write(tmp_path, [(f"deck{k}", Pos(0, 20 * k, 0) * two_color(30 + 10 * k)) for k in range(3)])
    meshes = bambu3mf.read_meshes(path)
    assert len(meshes) == 6
    sizes = bambu3mf.object_sizes(path)
    assert len({s for _, s in sizes}) == 3


def test_meshes_watertight_outward_and_in_place(tmp_path, two_color):
    part = two_color()
    path = _write(tmp_path, [("deck", part)])
    for (v, t), body in zip(bambu3mf.read_meshes(path).values(), part.children):
        edges = Counter(tuple(sorted(e)) for a, b, c in t for e in ((a, b), (b, c), (c, a)))
        assert set(edges.values()) == {2}
        vol = sum(np.dot(v[a], np.cross(v[b], v[c])) for a, b, c in t) / 6
        assert vol == pytest.approx(body.volume, rel=1e-3), "normals point out"


def test_same_objects_compares_with_a_tolerance_not_rounding(tmp_path):
    """Bambu saves 32-bit floats: 60.15 comes back as 60.149..., which rounds the other way. Compare within tol."""
    a = _write(tmp_path, [("b", box(0, 0, 0, 60.15, 10, 3))], "a")
    b = _write(tmp_path, [("b", box(0, 0, 0, 60.149, 10, 3))], "b")
    c = _write(tmp_path, [("b", box(0, 0, 0, 60.3, 10, 3))], "c")
    assert bambu3mf.same_objects(a, b)
    assert not bambu3mf.same_objects(a, c)


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_studio_reads_it_back_and_slices_one_color_change(tmp_path, two_color):
    path = _write(tmp_path, [("deck", two_color()), ("deck2", Pos(0, 20, 0) * two_color(60)),
                             ("block", Pos(0, 40, 0) * box(0, 0, 0, 20, 20, 3))])
    back = bambu.roundtrip(path, tmp_path / "rt.3mf")
    assert sorted(bambu3mf.read_filaments(back)) == sorted(bambu3mf.read_filaments(path))
    assert bambu3mf.same_objects(back, path)
    report = bambu.slice_report(_write(tmp_path, [("deck", two_color())], "deck"), tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (1,)]  # brown up to the seam, then gray: one change
    assert report["layers"][0][2] == round(2.4 / 0.2) - 1


PLA4 = [("PLA", "#E8862A"), ("PLA", "#F5C518"), ("PLA", "#161616"), ("PLA", "#5A3A1E")]


def test_filament_settings_set_type_and_color_per_slot(tmp_path):
    """Any filament set from the template: each slot copies a template slot of that type, then takes its color."""
    path = bambu3mf.write_settings(tmp_path / "s.config", PLA4)
    base, got = json.loads(bambu3mf.SETTINGS.read_text()), json.loads(path.read_text())
    assert got["filament_type"] == ["PLA"] * 4
    assert got["filament_colour"] == [c for _, c in PLA4]
    assert got["filament_settings_id"] == ["Bambu PLA Basic @BBL A1"] * 4
    assert got["nozzle_temperature"] == [base["nozzle_temperature"][2]] * 4  # PLA temps, not PETG's
    assert got["filament_self_index"] == base["filament_self_index"]
    assert got["printable_area"] == base["printable_area"]  # 4 long, but the bed, not filaments
    assert got["head_wrap_detect_zone"] == base["head_wrap_detect_zone"]


def test_settings_move_the_prime_tower(tmp_path):
    """A print that fills the bed leaves only a corner for the prime tower; the default spot would overlap it."""
    got = json.loads(bambu3mf.write_settings(tmp_path / "s.config", PLA4, tower=(4.0, 5.0, 30.0)).read_text())
    assert (got["wipe_tower_x"], got["wipe_tower_y"], got["prime_tower_width"]) == (["4.0"], ["5.0"], "30.0")
    base = json.loads(bambu3mf.SETTINGS.read_text())
    plain = json.loads(bambu3mf.write_settings(tmp_path / "p.config", PLA4).read_text())
    assert plain["wipe_tower_x"] == base["wipe_tower_x"] and plain["prime_tower_width"] == base["prime_tower_width"]


def test_filament_settings_need_a_type_the_template_has(tmp_path):
    with pytest.raises(ValueError, match="ABS"):
        bambu3mf.write_settings(tmp_path / "s.config", [("ABS", "#000000")] * 4)
    with pytest.raises(ValueError, match="4 filaments"):
        bambu3mf.write_settings(tmp_path / "s.config", PLA4[:3])


def test_write_plates_takes_project_settings(tmp_path, two_color):
    s = bambu3mf.write_settings(tmp_path / "s.config", PLA4)
    write_plates([Plate("pl", 1, [("deck", two_color())])], tmp_path, tmp_path / "p.csv", filament, settings=s, colors=4)
    proj = json.loads(zipfile.ZipFile(tmp_path / "pl.3mf").read("Metadata/project_settings.config"))
    assert proj["filament_colour"] == [c for _, c in PLA4]


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_with_written_filament_settings(tmp_path, two_color):
    s = bambu3mf.write_settings(tmp_path / "s.config", PLA4)
    write_plates([Plate("pl", 1, [("deck", two_color())])], tmp_path, tmp_path / "p.csv", filament, settings=s, colors=4)
    report = bambu.slice_report(tmp_path / "pl.3mf", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (1,)]
    assert set(report["grams"]) == {1, 2}


def _three_color():
    """Bodies stacked by height, three colors: two color changes, each a whole layer."""
    from build123d import Color, Compound
    a, b, c = box(0, 0, 0, 30, 30, 2), box(5, 5, 2, 20, 20, 2), box(10, 10, 4, 10, 10, 1)
    for body, name, col in ((a, "f_low", (0.9, 0.8, 0.1)), (b, "f_mid", (0.1, 0.1, 0.1)), (c, "f_top", (0.4, 0.2, 0.1))):
        body.label, body.color = name, Color(*col)
    return Compound(children=[a, b, c], label="flower")


def test_three_color_part_is_one_object_with_three_parts(tmp_path):
    fil = {"f_low": 2, "f_mid": 3, "f_top": 4}
    write_plates([Plate("pl", 1, [("flower", _three_color())])], tmp_path, tmp_path / "p.csv", fil.get, colors=4, color_changes=2)
    assert bambu3mf.read_filaments(tmp_path / "pl.3mf") == [("flower", 2, fil)]


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_three_colors_in_height_order(tmp_path):
    fil = {"f_low": 2, "f_mid": 3, "f_top": 4}
    s = bambu3mf.write_settings(tmp_path / "s.config", PLA4)
    write_plates([Plate("pl", 1, [("flower", _three_color())])], tmp_path, tmp_path / "p.csv", fil.get, settings=s,
                 colors=4, color_changes=2)
    report = bambu.slice_report(tmp_path / "pl.3mf", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (3,), (4,)]


def test_mesh_holds_curves_to_tol_in_mm_on_big_arcs():
    """tol is millimetres, not a fraction of each edge: an 18° arc of a 550 mm radius stays within 0.02 mm of true
    (build123d's own tessellate is relative, which put a corner deck's rails 0.14 mm inside its curve)."""
    import math
    from build123d import Axis, Plane, Rectangle, revolve
    ring = revolve(Plane.XZ * Pos(551, 1) * Rectangle(2, 2), Axis.Z, 18)
    v, t = bambu3mf.mesh(ring, tol=0.01)
    cen = v[t].mean(axis=1)
    rad = np.hypot(cen[:, 0], cen[:, 1])
    assert rad.min() >= 550 - 0.02, f"triangles {550 - rad.min():.3f} mm inside the inner face"


def test_moved_two_color_parts_are_written_where_they_were_placed(tmp_path, two_color):
    """A packer moves (and turns) each two-color Compound; its bodies must follow. They kept their first place once,
    so every ladder on a plate landed on the same spot and Bambu refused to slice ("gcode path conflicts")."""
    from build123d import Rot
    a = Pos(10, 10, 0) * two_color()
    b = Pos(150, 120, 0) * (Rot(0, 0, 90) * two_color())
    path = _write(tmp_path, [("deck", a), ("deck2", b)])
    box_of = lambda lo, hi: tuple(round(float(q), 1) for q in (*lo, *hi))
    written = sorted(box_of(v.min(axis=0), v.max(axis=0)) for v, _ in bambu3mf.read_meshes(path).values())
    placed = sorted(box_of((bb.min.X, bb.min.Y, bb.min.Z), (bb.max.X, bb.max.Y, bb.max.Z))
                    for part in (a, b) for body in part.children
                    for bb in [(part.location * body).bounding_box()])
    assert written == placed


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_a_plate_of_moved_two_color_parts(tmp_path, two_color):
    from build123d import Rot
    items = [("deck", Pos(10, 10, 0) * two_color()), ("deck2", Pos(150, 120, 0) * (Rot(0, 0, 90) * two_color()))]
    report = bambu.slice_report(_write(tmp_path, items), tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (1,)]


def test_writing_a_two_color_plate_over_the_tower_warns(tmp_path, two_color):
    with pytest.warns(UserWarning, match="prime tower"):
        _write(tmp_path, [("deck", Pos(40, 220, 0) * two_color())])


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_a_full_plate_of_two_color_parts(tmp_path, two_color):
    """A bed packed full of two-color parts slices: none sits where the prime tower prints."""
    from cadkit.plates import pack
    from cadkit import A1
    (pl, *_) = pack([(f"deck{i}", two_color(60.0)) for i in range(80)], A1, colors=4)  # a full first bed
    report = bambu.slice_report(_write(tmp_path, pl), tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (1,)]


# --- one project file with every plate (Bambu's multi-plate project, what MakerWorld takes) -----------------
def _kit(two_color):
    return [Plate("decks", 1, [("deck", Pos(10, 10, 0) * two_color()), ("deck2", Pos(10, 40, 0) * two_color())]),
            Plate("block", 1, [("block", box(100, 100, 0, 20, 20, 5))]),
            Plate("pegs", 3, [("peg", box(20, 20, 0, 5, 5, 8)), ("peg2", box(40, 20, 0, 5, 5, 8))])]


def test_combined_project_holds_every_plate_with_its_parts(tmp_path, two_color):
    write_plates(_kit(two_color), tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    path = tmp_path / "kit.3mf"
    assert bambu3mf.read_plates(path) == [("decks", ["deck", "deck2"]), ("block", ["block"]),
                                          ("pegs (print 3)", ["peg", "peg2"])]
    fil = {name: parts for name, _, parts in bambu3mf.read_filaments(path)}
    assert fil["deck"] == {"deck_wood": 2, "deck_steel": 1} and fil["peg"] == {"peg": 1}
    for name in ("decks", "block", "pegs"):  # the single-plate files are still written
        assert (tmp_path / f"{name}.3mf").exists()


def test_combined_plates_sit_in_bambus_plate_grid(tmp_path, two_color):
    """Bambu lays plates out left to right, then down, every 1.2 beds (measured on a MakerWorld project)."""
    write_plates(_kit(two_color), tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    w = 256 * 1.2
    cells = {name: xy for name, xy in bambu3mf.read_plate_offsets(tmp_path / "kit.3mf")}
    assert cells == {"decks": (0.0, 0.0), "block": (w, 0.0), "pegs (print 3)": (0.0, -w)}


def test_one_plate_kit_is_the_plain_project(tmp_path, two_color):
    kit = _kit(two_color)[:1]
    write_plates(kit, tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    assert bambu3mf.read_plates(tmp_path / "kit.3mf") == [("decks", ["deck", "deck2"])]
    assert bambu3mf.read_plate_offsets(tmp_path / "kit.3mf") == [("decks", (0.0, 0.0))]


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_keeps_and_slices_every_plate_of_a_combined_project(tmp_path, two_color):
    write_plates(_kit(two_color), tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    src = tmp_path / "kit.3mf"
    back = bambu.roundtrip(src, tmp_path / "rt.3mf")
    assert bambu3mf.read_plates(back) == bambu3mf.read_plates(src)
    assert bambu3mf.same_objects(back, src)
    reports = bambu.slice_all(src, tmp_path / "s.3mf")
    assert [[r[0] for r in rep["layers"]] for rep in reports] == [[(2,), (1,)], [(1,)], [(1,)]]
    names = zipfile.ZipFile(tmp_path / "s.3mf").namelist()
    assert {f"Metadata/plate_{i}.png" for i in (1, 2, 3)} <= set(names)  # the thumbnails MakerWorld shows


def test_combined_project_puts_every_plates_tower_in_the_kept_corner(tmp_path, two_color):
    """Bambu keeps a prime-tower spot per plate (lists in the project settings); every plate gets the one the packer
    keeps free."""
    write_plates(_kit(two_color), tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    proj = json.loads(zipfile.ZipFile(tmp_path / "kit.3mf").read("Metadata/project_settings.config"))
    tmpl = json.loads(bambu3mf.SETTINGS.read_text())
    assert proj["wipe_tower_x"] == tmpl["wipe_tower_x"][:1] * 3 and proj["wipe_tower_y"] == tmpl["wipe_tower_y"][:1] * 3


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_bambu_slices_a_two_color_plate_that_is_not_the_first(tmp_path, two_color):
    from cadkit import A1
    from cadkit.plates import pack
    full = pack([(f"deck{i}", two_color(60.0)) for i in range(80)], A1, colors=4)[0]  # a full bed, tower corner free
    kit = [Plate("block", 1, [("block", box(100, 100, 0, 20, 20, 5))]), Plate("decks", 1, full)]
    write_plates(kit, tmp_path, tmp_path / "p.csv", filament, colors=4, combined="kit")
    reports = bambu.slice_all(tmp_path / "kit.3mf", tmp_path / "s.3mf")
    assert [[r[0] for r in rep["layers"]] for rep in reports] == [[(1,)], [(2,), (1,)]]


def test_a_round_part_near_the_tower_corner_does_not_warn(tmp_path):
    """Only real overlap warns: a disc's bounding box reaches the tower corner, the disc doesn't (the 10" flower)."""
    import warnings
    from build123d import Align, Color, Compound, Cylinder
    lo = Pos(128, 118, 0) * Cylinder(95, 2.4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    hi = Pos(128, 118, 2.4) * Cylinder(20, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    lo.label, lo.color, hi.label, hi.color = "deck_wood", Color(0.4, 0.3, 0.2), "deck_steel", Color(0.6, 0.6, 0.6)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _write(tmp_path, [("disc", Compound(children=[lo, hi], label="disc"))])
