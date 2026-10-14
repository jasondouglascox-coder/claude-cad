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
