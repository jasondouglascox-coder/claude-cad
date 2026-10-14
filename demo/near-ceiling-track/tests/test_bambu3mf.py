"""Plates open in Bambu Studio already colored: each 3MF is a Bambu project with a filament per part
(brown wood, gray steel, white ceiling cleats), so nothing needs painting by hand."""
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from build123d import Pos

from hotrain import build
from hotrain import layout as L
from hotrain.params import INCH, P
from hotrain.parts import bracket, ceiling_anchor, tie_ladder
from hotrain.plates import Plate

D = replace(P, run_style="deck_truss")
CORE = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
BAMBU = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def _ladder():
    return tie_ladder.make_colored(D, [16 * INCH], L.segments(D, [16 * INCH])[1])


def _write(tmp_path, items, name="pl") -> zipfile.ZipFile:
    build.write_plates([Plate(name, 1, items)], tmp_path, tmp_path / "p.csv", p=D)
    return zipfile.ZipFile(tmp_path / f"{name}.3mf")


def settings(z: zipfile.ZipFile) -> dict:
    """{object name: (object filament, {part name: part filament})} from Metadata/model_settings.config.
    A part without its own filament uses the object's (Bambu Studio leaves it out for one-part objects)."""
    out = {}
    for o in ET.fromstring(z.read("Metadata/model_settings.config")).iter("object"):
        meta = {m.get("key"): m.get("value") for m in o.findall("metadata")}
        parts = {}
        for pt in o.findall("part"):
            pm = {m.get("key"): m.get("value") for m in pt.findall("metadata")}
            parts[pm["name"]] = int(pm.get("extruder", meta["extruder"]))
        out[meta["name"]] = (int(meta["extruder"]), parts)
    return out


def meshes(z: zipfile.ZipFile) -> list[tuple[list, list]]:
    out = []
    for n in z.namelist():
        if n.startswith("3D/Objects/"):
            for o in ET.fromstring(z.read(n)).iter(f"{CORE}object"):
                vs = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in o.iter(f"{CORE}vertex")]
                ts = [(int(t.get("v1")), int(t.get("v2")), int(t.get("v3"))) for t in o.iter(f"{CORE}triangle")]
                out.append((vs, ts))
    return out


def test_two_color_part_opens_brown_and_gray(tmp_path):
    z = _write(tmp_path, [("ladder", _ladder())])
    model = z.read("3D/3dmodel.model").decode()
    assert '<metadata name="Application">BambuStudio-' in model  # Bambu only reads part filaments from its own format
    assert model.count("<item ") == 1  # one object: the gray can't drop onto the bed
    assert settings(z) == {"ladder": (D.filament_brown, {"ladder_wood": D.filament_brown,
                                                         "ladder_steel": D.filament_gray})}
    proj = json.loads(z.read("Metadata/project_settings.config"))  # without it Bambu Studio's CLI crashes
    assert proj["printer_settings_id"] == "Bambu Lab A1 0.4 nozzle"
    assert len(proj["filament_colour"]) >= max(D.filament_gray, D.filament_brown, D.filament_white)


def test_single_color_parts_gray_and_cleats_white(tmp_path):
    z = _write(tmp_path, [("bracket", bracket.make(D)), ("ceiling_anchor", Pos(60, 0, 0) * ceiling_anchor.make(D))])
    got = settings(z)
    assert got["bracket"][0] == D.filament_gray and set(got["bracket"][1].values()) == {D.filament_gray}
    assert got["ceiling_anchor"][0] == D.filament_white


def test_meshes_watertight_outward_and_in_place(tmp_path):
    lad = _ladder()
    z = _write(tmp_path, [("ladder", lad)])
    ms = meshes(z)
    assert len(ms) == 2
    for (vs, ts), body in zip(ms, lad.children):
        edges = Counter()
        for a, b, c in ts:
            for e in ((a, b), (b, c), (c, a)):
                edges[tuple(sorted(e))] += 1
        assert set(edges.values()) == {2}, "every edge shared by exactly two triangles"
        vol = sum((vs[a][0] * (vs[b][1] * vs[c][2] - vs[b][2] * vs[c][1])
                   - vs[a][1] * (vs[b][0] * vs[c][2] - vs[b][2] * vs[c][0])
                   + vs[a][2] * (vs[b][0] * vs[c][1] - vs[b][1] * vs[c][0])) for a, b, c in ts) / 6
        assert vol == pytest.approx(body.volume, rel=1e-3), "normals point out"
        bb = body.bounding_box()
        for i, (lo, hi) in enumerate(((bb.min.X, bb.max.X), (bb.min.Y, bb.max.Y), (bb.min.Z, bb.max.Z))):
            assert min(v[i] for v in vs) == pytest.approx(lo, abs=0.01)
            assert max(v[i] for v in vs) == pytest.approx(hi, abs=0.01)


@pytest.mark.slow
@pytest.mark.skipif(not BAMBU.exists(), reason="Bambu Studio not installed")
def test_bambu_studio_keeps_the_filaments(tmp_path):
    """Bambu Studio itself loads the plate and saves it back with the same filament per part."""
    _write(tmp_path, [("ladder", _ladder()), ("bracket", Pos(0, 60, 0) * bracket.make(D))])
    out = tmp_path / "roundtrip.3mf"
    subprocess.run([str(BAMBU), "--export-3mf", str(out), str(tmp_path / "pl.3mf")], check=True,
                   capture_output=True, timeout=300, cwd=tmp_path)
    got = settings(zipfile.ZipFile(out))
    assert got["ladder"][1] == {"ladder_wood": D.filament_brown, "ladder_steel": D.filament_gray}
    assert got["bracket"][0] == D.filament_gray
