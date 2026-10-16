from cadkit import A1
from cadkit.plates import is_two_color, pack
from conftest import box


def test_packs_onto_few_plates_inside_the_bed():
    items = [(f"sq{i}", box(0, 0, 0, 120, 120, 3)) for i in range(5)]
    plates = pack(items)
    assert [len(p) for p in plates] == [4, 1]
    for p in plates:
        for _, s in p:
            bb = s.bounding_box()
            assert bb.min.X >= 0 and bb.min.Y >= 0 and bb.max.X <= A1.bed and bb.max.Y <= A1.bed


def test_two_color_parts_get_their_own_plates(two_color):
    plates = pack([("deck", two_color()), ("block", box(0, 0, 0, 20, 20, 3))])
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
    plates = pack([("flower", three), ("block", box(0, 0, 0, 20, 20, 3))])
    assert len(plates) == 2
