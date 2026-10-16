import pytest
from build123d import Box, Pos

from cadkit import A1, Printer
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems, unsupported
from cadkit.clash import find_clashes
from cadkit.shapes import bowtie, dovetail, poly, rect
from build123d import extrude
from conftest import box


def test_printable_box_and_each_problem():
    assert printable_problems(box(0, 0, 0, 20, 20, 3), A1) == []
    assert "not on the bed" in printable_problems(box(0, 0, 1, 20, 20, 3), A1)[0]
    assert "exceeds" in printable_problems(box(0, 0, 0, A1.usable + 1, 20, 3), A1)[0]
    assert "2 separate solids" in printable_problems(box(0, 0, 0, 5, 5, 3) + box(10, 0, 0, 5, 5, 3), A1)[0]
    assert printable_problems(box(0, 0, 0, 300, 20, 3), Printer(bed=350)) == []


def test_rectangular_bed_checks_each_side():
    bed = Printer(bed=250, bed_y=210, margin=5)
    assert printable_problems(box(0, 0, 0, 240, 20, 3), bed) == []
    assert "exceeds" in printable_problems(box(0, 0, 0, 20, 240, 3), bed)[0]


def test_clockwise_points_still_extrude_up():
    part = extrude(poly((0, 0), (0, 10), (10, 10), (10, 0)), 2)  # clockwise
    assert part.bounding_box().min.Z == pytest.approx(0) and len(part.solids()) == 1


def test_joint_shapes_grow_by_clearance():
    assert bowtie(10, 6, 3, 0.2).area > bowtie(10, 6, 3).area
    assert dovetail(0, 0, 3, 5, 4, 0.1).area > dovetail(0, 0, 3, 5, 4).area
    assert rect(0, 4, 0, 2).area == pytest.approx(8)


def test_watertight_and_layer_levels():
    assert open_edges(box(0, 0, 0, 10, 10, 2.4)) == 0
    assert off_layer_z(box(0, 0, 0, 10, 10, 2.4)) == []
    assert off_layer_z(box(0, 0, 0, 10, 10, 2.3)) == [2.3]


def test_upper_color_must_rest_on_lower():
    lower = box(0, 0, 0, 10, 10, 2)
    assert unsupported(box(2, 2, 2, 4, 4, 1), lower) == pytest.approx(0, abs=1e-9)
    assert unsupported(box(8, 2, 2, 4, 4, 1), lower) == pytest.approx(2 * 4 * 0.1)  # 2 mm hangs past the edge


def test_downward_faces_find_bridges():
    bridge = box(0, 0, 0, 2, 5, 3) + box(8, 0, 0, 2, 5, 3) + box(0, 0, 3, 10, 5, 1)
    assert downward_faces(bridge) == [(3.0, 30.0)]


def test_clashes_count_overlap_not_touching():
    a, b, c = box(0, 0, 0, 10, 10, 10), box(10, 0, 0, 10, 10, 10), box(5, 5, 5, 10, 10, 10)
    assert find_clashes([("a", a), ("b", b)]) == []
    assert [x[:2] for x in find_clashes([("a", a), ("c", c)])] == [("a", "c")]


def test_layer_levels_honor_a_thicker_first_layer():
    """Bambu's 0.16 mm profiles print a 0.2 mm first layer: boundaries are 0, 0.2, 0.36, 0.52, ..."""
    fine = Printer(layer=0.16, first_layer=0.2)
    assert fine.first == 0.2 and A1.first == A1.layer
    assert off_layer_z(box(0, 0, 0, 10, 10, 0.52), fine) == []
    assert off_layer_z(box(0, 0, 0, 10, 10, 0.48), fine) == [0.48]
    assert off_layer_z(box(0, 0, 0.2, 10, 10, 0.32), fine) == []  # 0.2 and 0.52 are boundaries
    assert off_layer_z(box(0, 0, 0.16, 10, 10, 0.2), fine) == [0.16]  # inside the first layer


def test_snap_puts_a_height_on_the_nearest_layer_boundary():
    assert A1.snap(3.0) == 3.0 and A1.snap(0.6) == 0.6 and A1.snap(0.29) == pytest.approx(0.2)
    fine = Printer(bed=256, layer=0.16, first_layer=0.2)
    assert fine.snap(3.0) == pytest.approx(0.2 + 18 * 0.16) and fine.on_layer(fine.snap(3.0))
    assert fine.snap(0.05) == pytest.approx(0.2)  # never below the first layer
    for z in (0.3, 0.6, 1.2, 2.4, 3.0, 15.0):
        assert fine.on_layer(fine.snap(z)) and abs(fine.snap(z) - z) <= 0.08 + 1e-9


def test_layers_rounds_a_stacked_thickness_to_whole_layers():
    fine = Printer(bed=256, layer=0.12, first_layer=0.2)
    base = fine.snap(3.0)
    assert fine.on_layer(base + fine.layers(0.6)) and fine.layers(0.6) == pytest.approx(0.6)
    assert fine.layers(0.01) == pytest.approx(0.12)  # at least one layer
    assert A1.layers(0.6) == 0.6 and A1.layers(15.0) == 15.0
