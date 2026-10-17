"""Every slicer cadkit knows passes the same contract. Adding one (PrusaSlicer, Cura, Orca...)? Register it in
cadkit/slicers/ and run these: the file tests always run; the live ones run when the slicer is installed."""
import pytest
from build123d import Pos

from cadkit import slicers
from cadkit.export import write_plates
from cadkit.plates import Plate
from conftest import box

FIL = {"deck_wood": 2, "deck_steel": 1}
ALL = sorted(slicers.SLICERS)


def _plate(tmp_path, slicer, items, name="pl"):
    write_plates([Plate(name, 1, items)], tmp_path, tmp_path / "p.csv", lambda n: FIL.get(n, 1), slicer=slicer,
                 colors=4, color_changes=99)  # a block beside the deck swaps every layer; fine for a file test
    return tmp_path / f"{name}{slicer.project_suffix}"


def test_bambu_is_the_default_and_none_is_there():
    assert {"bambu", "none"} <= set(ALL)
    assert slicers.get("bambu").name == "bambu"


def test_unknown_slicer_names_the_known_ones_and_how_to_add_one():
    with pytest.raises(ValueError, match="bambu.*CONTRIBUTING"):
        slicers.get("cura-but-misspelled")


def test_active_follows_settings(monkeypatch):
    from cadkit import settings
    monkeypatch.setenv("CADKIT_SLICER", "none")
    settings.reload()
    try:
        assert slicers.active().name == "none"
        assert not slicers.active().available()
    finally:
        monkeypatch.undo()
        settings.reload()
    assert slicers.active().name == settings.settings().slicer


@pytest.mark.parametrize("name", ALL)
def test_project_gives_each_body_its_filament(tmp_path, two_color, name):
    s = slicers.get(name)
    path = _plate(tmp_path, s, [("deck", two_color()), ("block", Pos(0, 20, 0) * box(0, 0, 0, 20, 20, 3))])
    assert sorted(s.read_filaments(path)) == [("block", 1, {"block": 1}), ("deck", 2, FIL)]


@pytest.mark.parametrize("name", ALL)
def test_unavailable_slicer_says_so_instead_of_crashing_oddly(tmp_path, two_color, name):
    s = slicers.get(name)
    if s.available():
        pytest.skip(f"{name} is installed")
    path = _plate(tmp_path, s, [("deck", two_color())])
    with pytest.raises(slicers.Unavailable, match=name):
        s.slice_report(path)


@pytest.mark.slow
@pytest.mark.parametrize("name", ALL)
def test_live_roundtrip_and_slice_one_color_change(tmp_path, two_color, name):
    s = slicers.get(name)
    if not s.available():
        pytest.skip(f"{name} not installed")
    path = _plate(tmp_path, s, [("deck", two_color()), ("block", Pos(0, 20, 0) * box(0, 0, 0, 20, 20, 3))])
    back = s.roundtrip(path, tmp_path / f"rt{s.project_suffix}")
    assert sorted(s.read_filaments(back)) == sorted(s.read_filaments(path))
    assert s.same_objects(back, path)
    report = s.slice_report(_plate(tmp_path, s, [("deck", two_color())], "deck"), tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(2,), (1,)]  # brown up to the seam, then gray: one change
    assert set(report["grams"]) == {1, 2}


def test_bambu_tower_keepout_covers_where_the_tower_prints():
    """Measured from Bambu's G-code with the A1 template: the tower printed in x 34.5-74.2, y 212.9-252.1
    (0.2 and 0.08 mm layers)."""
    x0, y0, x1, y1 = slicers.get("bambu").tower_keepout()
    assert x0 <= 34.5 - 2 and y0 <= 212.9 - 2 and x1 >= 74.2 + 2 and y1 >= 252.1


def test_a_slicer_without_a_tower_keeps_nothing_out():
    assert slicers.get("none").tower_keepout() is None
