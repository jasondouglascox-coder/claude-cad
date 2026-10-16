from cadkit import A1
from cadkit.plates import is_two_color, pack
from conftest import box


def test_packs_onto_few_plates_inside_the_bed():
    items = [(f"sq{i}", box(0, 0, 0, 120, 120, 3)) for i in range(5)]
    plates = pack(items, A1)
    assert [len(p) for p in plates] == [4, 1]
    for p in plates:
        for _, s in p:
            bb = s.bounding_box()
            assert bb.min.X >= 0 and bb.min.Y >= 0 and bb.max.X <= A1.bed and bb.max.Y <= A1.bed


def test_two_color_parts_get_their_own_plates(two_color):
    plates = pack([("deck", two_color()), ("block", box(0, 0, 0, 20, 20, 3))], A1, colors=4)
    assert len(plates) == 2
    assert all(len({is_two_color(s) for _, s in p}) == 1 for p in plates)


def test_multi_color_parts_get_their_own_plates():
    from build123d import Color, Compound
    from cadkit.plates import is_multi_color
    bodies = [box(0, 0, 0, 30, 30, 2), box(5, 5, 2, 20, 20, 2), box(10, 10, 4, 10, 10, 1)]
    for b in bodies:
        b.color = Color(0.5, 0.5, 0.5)
    three = Compound(children=bodies)
    assert is_multi_color(three)
    plates = pack([("flower", three), ("block", box(0, 0, 0, 20, 20, 3))], A1, colors=4)
    assert len(plates) == 2


def test_rectangular_bed_turns_parts_to_fit():
    from cadkit import Printer
    bed = Printer(bed=250, bed_y=210, margin=5)
    plates = pack([("long", box(0, 0, 0, 100, 240, 3))], bed)  # only fits lengthwise along X
    (_, s), = plates[0]
    bb = s.bounding_box()
    assert bb.max.X <= bed.bed and bb.max.Y <= bed.bed_y and bb.size.X > bb.size.Y


def test_pack_uses_the_printer_from_settings(monkeypatch):
    from cadkit import settings
    monkeypatch.setenv("CADKIT_BED", "130")
    settings.reload()
    try:
        assert [len(p) for p in pack([(f"sq{i}", box(0, 0, 0, 120, 120, 3)) for i in range(2)])] == [1, 1]
    finally:
        monkeypatch.undo()
        settings.reload()


def test_one_color_printer_mixes_multi_color_parts_with_the_rest(two_color):
    assert len(pack([("deck", two_color()), ("block", box(0, 0, 0, 20, 20, 3))], A1, colors=1)) == 1
