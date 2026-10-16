"""Colors are a budget, not a law: count the swaps a plate costs, say when it's over the setup's limits (and what
to do instead), and print on a one-color printer without complaint."""
import warnings

import pytest
from build123d import Color, Compound, Pos

from cadkit import bambu3mf
from cadkit.checks import color_problems
from cadkit.export import write_plates
from cadkit.plates import Plate, color_changes
from conftest import box

YELLOW, ORANGE, BLACK = Color(0.96, 0.77, 0.09), Color(0.91, 0.53, 0.16), Color(0.09, 0.09, 0.09)
FIL = {"deck_wood": 2, "deck_steel": 1, "f_low": 2, "f_bead": 1, "f_top": 3}


def _part(*bodies):
    for b, name, col in bodies:
        b.label, b.color = name, col
    return Compound(children=[b for b, _, _ in bodies], label="f")


def _beads():
    """Yellow with orange beads in the same layers, then black on top: every bead layer swaps twice."""
    return _part((box(0, 0, 0, 30, 30, 1), "f_low", YELLOW), (box(40, 0, 0, 5, 5, 1), "f_bead", ORANGE),
                 (box(5, 5, 1, 10, 10, 0.4), "f_top", BLACK))


def test_stacked_colors_change_once_per_seam(two_color):
    assert color_changes(two_color()) == 1
    assert color_changes(box(0, 0, 0, 5, 5, 2)) == 0
    assert color_changes([("a", two_color()), ("b", Pos(0, 20, 0) * two_color(60))]) == 1  # same seam: one swap


def test_colors_side_by_side_change_every_layer():
    # 5 layers yellow+orange: yellow, orange | orange, yellow | ... = 1 swap per layer (start with the last one),
    # then black on top: 1 more
    assert color_changes(_beads()) == 5 + 1


def test_within_budget_is_no_problem(two_color):
    assert color_problems([("deck", two_color())], colors=4, changes=1) == []


def test_over_budget_says_how_many_and_what_to_do(two_color):
    probs = color_problems([("f", _beads())], colors=4, changes=1)
    assert len(probs) == 1 and "6 color changes" in probs[0] and "CADKIT_COLOR_CHANGES" in probs[0]
    assert "split" in probs[0] and "glue" in probs[0]
    probs = color_problems([("deck", two_color())], colors=1, changes=1)
    assert "2 colors" in probs[0] and "CADKIT_COLORS" in probs[0]


def test_budget_comes_from_settings(monkeypatch, two_color):
    from cadkit import settings
    assert color_problems([("f", _beads())])  # defaults: 4 colors, 1 change
    monkeypatch.setenv("CADKIT_COLOR_CHANGES", "10")
    settings.reload()
    try:
        assert color_problems([("f", _beads())]) == []
    finally:
        monkeypatch.undo()
        settings.reload()


def test_one_color_printer_gets_every_part_on_filament_1(tmp_path, two_color, monkeypatch):
    from cadkit import settings
    monkeypatch.setenv("CADKIT_COLORS", "1")
    settings.reload()
    try:
        write_plates([Plate("pl", 1, [("deck", two_color())])], tmp_path, tmp_path / "p.csv", FIL.get)
    finally:
        monkeypatch.undo()
        settings.reload()
    assert bambu3mf.read_filaments(tmp_path / "pl.3mf") == [("deck", 1, {"deck_wood": 1, "deck_steel": 1})]


def test_more_filaments_than_the_printer_has_stops_with_options(tmp_path, two_color):
    with pytest.raises(ValueError, match="filament 3.*2 colors.*CADKIT_COLORS"):
        write_plates([Plate("pl", 1, [("f", _beads())])], tmp_path, tmp_path / "p.csv", FIL.get, colors=2)


def test_plate_over_the_change_budget_warns_but_still_writes(tmp_path):
    with pytest.warns(UserWarning, match="pl: 6 color changes"):
        write_plates([Plate("pl", 1, [("f", _beads())])], tmp_path, tmp_path / "p.csv", FIL.get)
    assert (tmp_path / "pl.3mf").exists()
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # a project that accepts the cost says so
        write_plates([Plate("pl", 1, [("f", _beads())])], tmp_path, tmp_path / "p.csv", FIL.get, color_changes=6)


def test_count_filaments_not_colors(two_color):
    """An uncolored block on filament 1 beside a deck whose gray tops are filament 1 too: brown and gray share the
    lower layers, so every one of them swaps."""
    plate = [("deck", two_color()), ("block", Pos(0, 20, 0) * box(0, 0, 0, 20, 20, 3))]
    fil = lambda name, body: FIL.get(name, 1)
    assert color_changes(plate, key=fil) == 12 + 1 - 1  # 12 two-filament layers, then gray carries on


def test_a_plate_can_accept_its_own_cost(tmp_path, two_color):
    """The design accepts the beads' swaps on that plate only; another plate over budget still warns."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        write_plates([Plate("beads", 1, [("f", _beads())], color_changes=6), Plate("deck", 1, [("d", two_color())])],
                     tmp_path, tmp_path / "p.csv", FIL.get)
