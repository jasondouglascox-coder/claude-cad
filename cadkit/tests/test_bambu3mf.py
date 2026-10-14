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
    write_plates([Plate(name, 1, items)], tmp_path, tmp_path / "p.csv", filament)
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
