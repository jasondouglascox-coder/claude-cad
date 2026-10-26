"""This project's plates open in the slicer already colored: brown wood, gray steel, white ceiling cleats.
(The 3MF format itself is tested in cadkit.)"""
from dataclasses import replace

import pytest
from build123d import Pos

from cadkit import slicers
from cadkit.settings import settings
from hotrain import build
from hotrain import layout as L
from hotrain.params import INCH, P
from hotrain.parts import bracket, ceiling_anchor, tie_ladder
from hotrain.plates import Plate

D = replace(P, run_style="deck_truss")


def _write(tmp_path, items, name="pl"):
    build.write_plates([Plate(name, 1, items, color_changes=99)], tmp_path, tmp_path / "p.csv", p=D)
    return tmp_path / f"{name}{slicers.active().project_suffix}"  # mixed plates here: swaps don't matter


def test_ladder_opens_brown_and_gray(tmp_path):
    lad = tie_ladder.make_colored(D, [16 * INCH], L.segments(D, [16 * INCH])[1])
    f = settings().filament
    assert slicers.active().read_filaments(_write(tmp_path, [("ladder", lad)])) == [
        ("ladder", f(D.filament_brown), {"ladder_wood": f(D.filament_brown), "ladder_steel": f(D.filament_gray)})]


def test_single_color_parts_gray_and_cleats_white(tmp_path):
    got = {n: f for n, f, _ in slicers.active().read_filaments(
        _write(tmp_path, [("bracket", bracket.make(D)), ("ceiling_anchor", Pos(60, 0, 0) * ceiling_anchor.make(D))]))}
    f = settings().filament
    assert got == {"bracket": f(D.filament_gray), "ceiling_anchor": f(D.filament_white)}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_a_runs_ladders_survive_the_slicer(tmp_path):
    """A 16" run's three ladders open as three different ladders (only the middle one has the solder gap),
    each brown and gray."""
    segs = L.segments(D, [16 * INCH])
    items = [(f"ladder_{k:02d}", Pos(0, 50 * k, 0) * tie_ladder.make_colored(D, [16 * INCH], s))
             for k, s in enumerate(segs)]
    path = _write(tmp_path, items + [("bracket", Pos(90, 160, 0) * bracket.make(D))])  # clear of the prime tower
    s = slicers.active()
    back = s.roundtrip(path, tmp_path / f"rt{s.project_suffix}")
    assert s.same_objects(back, path)
    if s.name == "bambu":
        from cadkit import bambu3mf
        assert len({sz for n, sz in bambu3mf.object_sizes(back) if n.startswith("ladder")}) == 3
    assert sorted(s.read_filaments(back)) == sorted(s.read_filaments(path))
    # and it slices: every two-color ladder was once written on the same spot ("gcode path conflicts")
    rep = s.slice_report(path, tmp_path / f"s{s.project_suffix}")
    assert {f for fils, _, _ in rep["layers"] for f in fils} == {D.filament_brown, D.filament_gray}
