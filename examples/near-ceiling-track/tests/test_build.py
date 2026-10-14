import pytest
import csv

from hotrain import build
from hotrain import layout as L
from hotrain.params import P

pytestmark = pytest.mark.slow  # minutes per test: run with -m slow or the full suite


def read_manifest(out):
    with open(out / "manifest.csv", encoding="utf-8") as f:
        return {r["file"]: int(r["quantity"]) for r in csv.DictReader(f)}


def test_parts_writes_step_per_part_and_manifest(tmp_path):
    assert build.main(["parts", "--out", str(tmp_path)]) == 0
    m = read_manifest(tmp_path)
    nb = len(L.BAYS)
    assert m["step/bracket.step"] == nb + 1
    assert m["step/keystone.step"] == 2 * nb
    assert m["step/end_pier.step"] == 4
    assert sum(q for f, q in m.items() if "arch_half" in f) == 4 * nb
    assert sum(1 for f in m if "ladder_" in f) == len(L.segments(P, L.BAYS))
    for f in m:
        text = (tmp_path / f).read_text()[:200]
        assert text.startswith("ISO-10303-21"), f


def test_fit_test_and_previews(tmp_path):
    assert build.main(["fit-test", "--out", str(tmp_path), "--preview", "--mesh"]) == 0
    assert (tmp_path / "step" / "fit_test.step").stat().st_size > 1000
    assert (tmp_path / "stl" / "fit_test.stl").stat().st_size > 1000
    assert "<svg" in (tmp_path / "preview" / "fit_test.svg").read_text()[:500]


def test_check_reports_clean_run(capsys):
    assert build.main(["check"]) == 0
    assert "no clashes" in capsys.readouterr().out


def test_assembly_step_carries_part_names(tmp_path):
    assert build.main(["assembly", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "step" / "run_assembly.step").read_text()
    import re
    products = set(re.findall(r"PRODUCT\('([^']*)'", text))
    assert {"arch_half_406.4mm", "bracket", "end_pier", "keystone", "ladder_01"} <= products
    assert not any(n.startswith("bay0_") for n in products)  # no instance names masquerading as parts
    assert "SI_UNIT(.MILLI.,.METRE.)" in text


def test_part_step_named_after_part(tmp_path):
    import re
    assert build.main(["parts", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "step" / "bracket.step").read_text()
    assert "bracket" in set(re.findall(r"PRODUCT\('([^']*)'", text))


def test_plates_writes_step_3mf_and_list(tmp_path):
    assert build.main(["plates", "--out", str(tmp_path)]) == 0
    with open(tmp_path / "plates.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    viaduct = [r for r in rows if r["plate"].startswith(("bay_", "run_ends"))]
    assert len(viaduct) == 3 and sum(int(r["quantity"]) for r in viaduct) == 3
    assert any(r["plate"].startswith("ladders") for r in rows)
    assert {"rod_jig"} <= {r["plate"] for r in rows}
    assert any(r["plate"].startswith("inside_corner") and r["quantity"] == "3" for r in rows)
    for r in rows:
        assert (tmp_path / "plates" / f"{r['plate']}.step").read_text()[:12] == "ISO-10303-21"
        assert (tmp_path / "plates" / f"{r['plate']}.3mf").stat().st_size > 1000


def test_all_writes_two_bay_demo(tmp_path):
    assert build.main(["all", "--out", str(tmp_path)]) == 0
    import re
    text = (tmp_path / "step" / "demo_two_bays.step").read_text()
    products = set(re.findall(r"PRODUCT\('([^']*)'", text))
    assert {"arch_half_406.4mm", "bracket", "ladder_02"} <= products  # 2 bays -> at least 5 ladders


def test_corners_writes_parts_assemblies_and_layout(tmp_path):
    import re
    assert build.main(["corners", "--out", str(tmp_path)]) == 0
    d = tmp_path / "corners"
    for name in ("corner_deck_curve", "corner_frame_inner", "floor_beam", "rod_anchor", "deep_bracket",
                 "rod_jig", "inside_corner_assembly", "bridge_corner_assembly"):
        assert (d / f"{name}.step").read_text()[:12] == "ISO-10303-21", name
    products = set(re.findall(r"PRODUCT\('([^']*)'", (d / "bridge_corner_assembly.step").read_text()))
    assert {"corner_deck_curve", "corner_frame_outer", "floor_beam", "aluminum_rod_inner"} <= products
    with open(tmp_path / "corners_layout.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert any(r["item"].startswith("ceiling anchor") for r in rows)
