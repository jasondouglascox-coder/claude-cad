"""Print readiness of the starter bay: every part watertight, flat, on the bed; at most one color change per
plate (two-color parts never share a plate with single-color parts)."""
from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
from build123d import Compound

from hotrain import plates
from hotrain.params import INCH, P

D = replace(P, run_style="deck_truss")


def non_manifold_edges(shape, tol=1e-4) -> int:
    bad = 0
    for s in shape.solids():
        verts, tris = s.tessellate(0.05, 0.2)
        V = np.round(np.array([(v.X, v.Y, v.Z) for v in verts]) / tol).astype(np.int64)
        _, idx = np.unique(V, axis=0, return_inverse=True)
        idx = idx.ravel()
        edges = Counter()
        for t in tris:
            a, b, c = (int(idx[i]) for i in t)
            for e in ((a, b), (b, c), (c, a)):
                edges[tuple(sorted(e))] += 1
        bad += sum(1 for n in edges.values() if n != 2)
    return bad


@pytest.fixture(scope="module")
def starter():
    return plates.all_in_one(D, [16 * INCH])


@pytest.mark.slow
def test_starter_parts_watertight_flat_on_bed(starter):
    for pl in starter:
        for name, s in pl.items:
            bb = s.bounding_box()
            assert bb.min.Z == pytest.approx(0, abs=1e-6), name
            assert 0 <= bb.min.X and bb.max.X <= P.bed and 0 <= bb.min.Y and bb.max.Y <= P.bed, name
            bodies = s.children if plates.is_two_color(s) else [s]
            for b in bodies:
                assert b.is_valid, name
                assert non_manifold_edges(b) == 0, name


def test_at_most_one_color_change_per_plate(starter):
    for pl in starter:
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
