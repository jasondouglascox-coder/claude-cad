"""Test first: the jig prints flat, its straight edges run through the pivot, and every pencil hole draws the circle
its label says, all derived from params."""
import math

import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from circle_jig import build
from circle_jig.params import INCH, P
from circle_jig.parts import jig, on_bed

LOW = 0.1  # probe height: the bottom, where the pencil runs


@pytest.fixture(scope="module")
def part():
    return jig(P)


def pieces(part, x0, x1, y0, y1, z=LOW):
    """Solid pieces (bounding boxes) of the part inside a thin probe box at height z."""
    probe = Pos(x0, y0, z - 0.05) * Box(x1 - x0, y1 - y0, 0.1, align=(Align.MIN,) * 3)
    return [s.bounding_box() for s in (part & probe).solids()]


def test_prints_flat_watertight_on_layers():
    b = on_bed(P)
    assert printable_problems(b, P.printer) == []
    assert open_edges(b) == 0
    assert off_layer_z(b, P.printer) == []
    assert downward_faces(b) == []


def test_pivot_hole_centred_on_the_origin(part):
    a, b = sorted(pieces(part, -P.w / 2, P.w / 2, -0.05, 0.05), key=lambda bb: bb.min.X)
    assert (a.max.X, b.min.X) == pytest.approx((-P.pivot_d / 2, P.pivot_d / 2), abs=0.02)


# each straight edge: the way its arm runs from the pivot, and which side of the line is open for the pencil
EDGES = [((1, 0), (0, -1)), ((0, 1), (1, 0)), ((-1, 0), (0, 1)), ((0, -1), (-1, 0))]


@pytest.mark.parametrize("k", range(4))
def test_straight_edges_run_through_the_pivot(part, k):
    """Along each arm, a thin probe across the edge: the part stops exactly on the line through the pivot, from the
    hub out to the tip."""
    (dx, dy), (ox, oy) = EDGES[k]
    reach = P.bar_len if k == 0 else P.arm
    for s in (P.w + 1, (P.w + reach) / 2, reach - 1):
        if dx:  # runs along X: probe across Y
            (bb,) = pieces(part, dx * s - 0.05, dx * s + 0.05, -5, 5)
            edge = bb.min.Y if oy < 0 else bb.max.Y
        else:
            (bb,) = pieces(part, -5, 5, dy * s - 0.05, dy * s + 0.05)
            edge = bb.min.X if ox < 0 else bb.max.X
        assert edge == pytest.approx(0, abs=1e-3)


@pytest.mark.parametrize("d", P.diameters_in)
def test_pencil_hole_draws_its_circle(part, d):
    """At the bottom, the throat's gap along the bar is centred so the hole is d/2 inches from the pivot."""
    r = d * INCH / 2
    x = P.hole_x(r)
    a, b = sorted(pieces(part, x - 6, x + 6, P.hole_off - 0.05, P.hole_off + 0.05), key=lambda bb: bb.min.X)
    assert b.min.X - a.max.X == pytest.approx(P.throat_d, abs=0.02)
    centre = (a.max.X + b.min.X) / 2
    assert math.hypot(centre, P.hole_off) == pytest.approx(r, abs=0.01)


def test_top_is_bevelled_along_the_straight_edge(part):
    """Like a ruler: at the top the bar starts a bevel's width in from the edge, at the bottom right on it."""
    x = (P.w + P.bar_len) / 2
    (top,) = pieces(part, x - 0.05, x + 0.05, -5, P.w / 2, z=P.t - 0.1)
    assert top.min.Y == pytest.approx(P.bevel - 0.1, abs=0.05)


def test_build_writes_an_orange_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "render" / "iso.png").exists() and (tmp_path / "step" / "circle_jig.step").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"circle_jig_1{s.project_suffix}")}
    assert got == {"circle_jig": P.filament}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_prints_it_in_one_filament_with_no_supports(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    project = tmp_path / "plates" / f"circle_jig_1{s.project_suffix}"
    assert s.same_objects(project, s.roundtrip(project, tmp_path / "rt.3mf"))
    report = s.slice_report(project, tmp_path / "s.3mf")
    assert {f for layer in report["layers"] for f in layer[0]} == {P.filament}
