"""This project's plates open in Bambu Studio already colored: brown wood, gray steel, white ceiling cleats.
(The 3MF format itself is tested in cadkit.)"""
from dataclasses import replace

import pytest
from build123d import Pos

from cadkit import bambu, bambu3mf
from hotrain import build
from hotrain import layout as L
from hotrain.params import INCH, P
from hotrain.parts import bracket, ceiling_anchor, tie_ladder
from hotrain.plates import Plate

D = replace(P, run_style="deck_truss")


def _write(tmp_path, items, name="pl"):
    build.write_plates([Plate(name, 1, items)], tmp_path, tmp_path / "p.csv", p=D)
    return tmp_path / f"{name}.3mf"


def test_ladder_opens_brown_and_gray(tmp_path):
    lad = tie_ladder.make_colored(D, [16 * INCH], L.segments(D, [16 * INCH])[1])
    assert bambu3mf.read_filaments(_write(tmp_path, [("ladder", lad)])) == [
        ("ladder", D.filament_brown, {"ladder_wood": D.filament_brown, "ladder_steel": D.filament_gray})]


def test_single_color_parts_gray_and_cleats_white(tmp_path):
    got = {n: f for n, f, _ in bambu3mf.read_filaments(
        _write(tmp_path, [("bracket", bracket.make(D)), ("ceiling_anchor", Pos(60, 0, 0) * ceiling_anchor.make(D))]))}
    assert got == {"bracket": D.filament_gray, "ceiling_anchor": D.filament_white}


@pytest.mark.slow
@pytest.mark.skipif(bambu.find() is None, reason="Bambu Studio not installed")
def test_starter_ladders_survive_bambu_studio(tmp_path):
    """The starter bay's three ladders open as three different ladders (only the middle one has the solder gap),
    each brown and gray."""
    segs = L.segments(D, [16 * INCH])
    items = [(f"ladder_{k:02d}", Pos(0, 50 * k, 0) * tie_ladder.make_colored(D, [16 * INCH], s))
             for k, s in enumerate(segs)]
    path = _write(tmp_path, items + [("bracket", Pos(0, 160, 0) * bracket.make(D))])
    back = bambu.roundtrip(path, tmp_path / "rt.3mf")
    assert bambu3mf.object_sizes(back) == bambu3mf.object_sizes(path)
    assert len({s for n, s in bambu3mf.object_sizes(back) if n.startswith("ladder")}) == 3
    assert sorted(bambu3mf.read_filaments(back)) == sorted(bambu3mf.read_filaments(path))
