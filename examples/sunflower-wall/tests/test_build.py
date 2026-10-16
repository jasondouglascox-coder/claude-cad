"""Plates: what to print and how many, files that open colored in the slicer, and what the slicer makes of them."""
import pytest

from cadkit import slicers
from cadkit.settings import settings
from sunflower import build, plates
from sunflower.params import P


@pytest.fixture(scope="module")
def plans():
    return plates.plans(P)


def test_nine_prints_on_three_plate_designs(plans):
    got = {pl.name: (pl.qty, sorted(n.split("#")[0] for n, _ in pl.items)) for pl in plans}
    assert got == {"back_quarter": (4, ["back_quarter", "pin", "pin", "pin"]),
                   "front_quarter": (4, ["front_quarter"]),
                   "seed_head": (1, ["center"])}
    assert sum(pl.qty for pl in plans) == 9
    assert 4 * sum(n.startswith("pin") for n, _ in plans[0].items) == 12  # 8 needed, 4 spare


def test_filament_per_part_matches_the_ams():
    f = plates.filament_for(P)
    assert (f("back_quarter"), f("front_quarter"), f("pin#2")) == (P.slot_petals, P.slot_petals, P.slot_pins)
    assert f("front_beads") == P.slot_beads
    assert (f("center_black"), f("center_brown")) == (P.slot_center, P.slot_seeds)


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("out")
    assert build.main(["plates", "--out", str(d)]) == 0
    return d


@pytest.mark.slow
def test_plates_open_colored_with_the_users_filaments(out):
    s, f = slicers.active(), settings().filament
    plate = lambda name: out / "plates" / f"{name}{s.project_suffix}"
    got = {name: parts for name, _, parts in s.read_filaments(plate("seed_head"))}
    assert got["center"] == {"center_black": f(P.slot_center), "center_brown": f(P.slot_seeds)}
    front = s.read_filaments(plate("front_quarter"))
    assert front == [("front_quarter", f(P.slot_petals),
                      {"front_quarter": f(P.slot_petals), "front_beads": f(P.slot_beads)})]
    back = s.read_filaments(plate("back_quarter"))
    assert sorted(fil for _, fil, _ in back) == [f(P.slot_petals)] * 4
    import json, zipfile
    proj = json.loads(zipfile.ZipFile(out / "plates" / "back_quarter.3mf").read("Metadata/project_settings.config"))
    assert proj["filament_colour"] == [c for _, c in P.filaments]
    assert proj["filament_type"] == [t for t, _ in P.filaments]
    assert (out / "plates.csv").read_text().count("\n") == 4


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
@pytest.mark.skipif(settings().colors < 4, reason="designed for 4 colors")
@pytest.mark.parametrize("name,bands", [
    ("back_quarter", [{P.slot_petals}]),
    # the beads share layers with the yellow: a swap on each of those layers (spec amendment, 2026-10-16)
    ("front_quarter", [{P.slot_petals}, {P.slot_petals, P.slot_beads}, {P.slot_petals}]),
    ("seed_head", [{P.slot_center}, {P.slot_seeds}])])
def test_slicer_slices_each_plate_in_its_colors(out, tmp_path, name, bands):
    s = slicers.active()
    src = out / "plates" / f"{name}{s.project_suffix}"
    back = s.roundtrip(src, tmp_path / f"rt{s.project_suffix}")
    assert s.same_objects(back, src)
    report = s.slice_report(src, tmp_path / "s.3mf")
    assert [set(r[0]) for r in report["layers"]] == bands


@pytest.mark.slow
def test_assembly_step_opens_as_the_whole_flower(tmp_path):
    """One STEP for Onshape: every part placed, named by part type, colored."""
    from build123d import import_step
    from sunflower import layout
    assert build.main(["step", "--out", str(tmp_path)]) == 0
    flower = import_step(str(tmp_path / "step" / "sunflower_assembly.step"))
    solids = flower.solids()
    assert len(solids) == 8 + 1 + len(layout.seeds(P)) + 8
    bb = flower.bounding_box()
    assert bb.size.X == pytest.approx(P.diameter, abs=2) and bb.min.Z == pytest.approx(0, abs=1e-3)
    names = {c.label for c in flower.children}
    assert {"back_quarter", "front_quarter", "seed_head", "pin"} <= names


@pytest.mark.slow
def test_build_small_writes_the_10_inch_print(tmp_path):
    assert build.main(["small", "--out", str(tmp_path)]) == 0
    d = tmp_path / "small"
    assert (d / "plates" / "sunflower_10in.3mf").exists() and (d / "sunflower_10in.step").exists()
    assert (d / "render" / "front.png").exists() and (d / "render" / "iso.png").exists()
