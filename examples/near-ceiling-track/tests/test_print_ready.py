"""Print readiness of a room section (the first 418 mm bay of a run): every part watertight, flat, on the bed; at most
one color change per plate (two-color parts never share a plate with single-color parts)."""
from dataclasses import replace

import pytest
from build123d import Compound

from cadkit.checks import open_edges
from hotrain import plates
from hotrain.params import INCH, P

D = replace(P, run_style="deck_truss")


@pytest.fixture(scope="module")
def section():
    sec = next(s for s in plates.sections(D) if s.name == "section_418mm_first")
    return plates.section_plates(D, sec)


@pytest.mark.slow
def test_section_parts_watertight_flat_on_bed(section):
    for pl in section:
        for name, s in pl.items:
            bb = s.bounding_box()
            assert bb.min.Z == pytest.approx(0, abs=1e-6), name
            assert 0 <= bb.min.X and bb.max.X <= P.printer.bed and 0 <= bb.min.Y and bb.max.Y <= P.bed_y, name
            bodies = s.children if plates.is_two_color(s) else [s]
            for b in bodies:
                assert b.is_valid, name
                assert open_edges(b) == 0, name


def test_at_most_one_color_change_per_plate(section):
    for pl in section:
        two = [s for _, s in pl.items if plates.is_two_color(s)]
        assert not two or len(two) == len(pl.items), f"{pl.name} mixes two-color and single-color parts"
        if two:
            top_of_brown = max(s.children[0].bounding_box().max.Z for s in two)
            bottom_of_gray = min(s.children[1].bounding_box().min.Z for s in two)
            assert top_of_brown <= bottom_of_gray + 1e-6, pl.name


def test_two_color_part_is_one_3mf_object(tmp_path):
    """Brown + gray bodies of a ladder must be ONE build item (two parts), or the slicer drops the gray
    tie plates onto the bed."""
    import zipfile
    from hotrain import build
    from hotrain.plates import Plate
    from hotrain import layout as L
    from hotrain.parts import tie_ladder
    seg = L.segments(D, [16 * INCH])[1]
    lad = tie_ladder.make_colored(D, [16 * INCH], seg)
    build.write_plates([Plate("lad", 1, [("ladder", lad)])], tmp_path, tmp_path / "p.csv")
    xml = zipfile.ZipFile(tmp_path / "lad.3mf").read("3D/3dmodel.model").decode()
    assert xml.count("<item ") == 1
    assert xml.count("<component ") >= 2
