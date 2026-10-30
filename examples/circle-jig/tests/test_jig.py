"""Test first: the jig prints flat in two pieces joined by a dovetail tab, its straight edges run through the pivot, and every pencil
hole sits the inches from the screw its number says, all derived from params."""
import math

import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.clash import find_clashes
from circle_jig import build
from circle_jig.params import INCH, P
from circle_jig.parts import extension, hub, jig, plates

LOW = 0.1  # probe height: the bottom, where the pencil runs


@pytest.fixture(scope="module")
def part():
    return jig(P)


@pytest.fixture(scope="module")
def pieces2():
    return hub(P), extension(P)


def pieces(part, x0, x1, y0, y1, z=LOW):
    """Solid pieces (bounding boxes) of the part inside a thin probe box at height z."""
    probe = Pos(x0, y0, z - 0.05) * Box(x1 - x0, y1 - y0, 0.1, align=(Align.MIN,) * 3)
    return [s.bounding_box() for s in (part & probe).solids()]


@pytest.mark.parametrize("plate", range(len(plates(P))))
def test_every_plate_prints_flat_watertight_on_layers_with_room_round_it(plate):
    bed_x, bed_y = P.printer.bed, P.printer.bed_y or P.printer.bed
    for name, b in plates(P)[plate].items:
        assert printable_problems(b, P.printer) == [], name
        assert open_edges(b) == 0, name
        assert off_layer_z(b, P.printer) == [], name
        assert downward_faces(b) == [], name
        bb = b.bounding_box()
        assert min(bb.min.X, bb.min.Y, bed_x - bb.max.X, bed_y - bb.max.Y) >= P.printer.margin / 2, name


def test_two_plates_of_one_piece_each():
    assert [len(pl.items) for pl in plates(P)] == [1, 1]


def test_pieces_make_the_whole_jig(part, pieces2):
    """Assembled, they're the one-piece jig less the tab's fit gap, and touch nowhere but face to face."""
    assert find_clashes([("hub", pieces2[0]), ("extension", pieces2[1])]) == []
    total = sum(x.volume for x in pieces2)
    assert total == pytest.approx(part.volume, rel=1e-4, abs=4 * P.fit_tab * P.tab_len * P.t)  # text: volume noise


def test_seam_and_tab_fall_between_holes(pieces2):
    """The butt seam at split_x; the extension's tab reaches back into the hub, clear of the last hub hole."""
    h, e = pieces2
    assert e.bounding_box().min.X == pytest.approx(P.split_x - P.tab_len, abs=1e-3)
    assert h.bounding_box().max.X == pytest.approx(P.split_x, abs=1e-3)
    assert P.hole_x(P.split_after * INCH) + P.sink_r < P.split_x - P.tab_len - P.fit_tab
    assert P.hole_x((P.split_after + 1) * INCH) - P.sink_r > P.split_x


def test_tab_fits_its_socket_with_the_fit(pieces2):
    """Across the neck on the seam: the socket is the tab's neck plus the fit each side."""
    h, e = pieces2
    flare = (P.tab_head - P.tab_neck) / P.tab_len  # extra width per mm away from the neck
    (tb,) = pieces(e, P.split_x - 0.002, P.split_x, 0, P.w, z=P.t / 2)
    assert tb.max.Y - tb.min.Y == pytest.approx(P.tab_neck, abs=0.01 + flare * 0.002)
    a, b = sorted(pieces(h, P.split_x - 0.002, P.split_x, -1, P.w + 1, z=P.t / 2), key=lambda bb: bb.min.Y)
    assert b.min.Y - a.max.Y == pytest.approx(P.tab_neck + 2 * P.fit_tab, abs=0.01 + flare * 0.002)


def test_tab_locks_the_pieces_together(pieces2):
    """The tab's head is wider than its neck, so the extension can't pull straight off the hub."""
    h, e = pieces2
    x = P.split_x - P.tab_len + 0.5
    (tb,) = pieces(e, x - 0.001, x + 0.001, 0, P.w, z=P.t / 2)
    assert tb.max.Y - tb.min.Y > P.tab_neck + 2 * P.fit_tab + 1


def test_pivot_hole_centred_on_the_origin(part):
    a, b = sorted(pieces(part, -P.w / 2, P.w / 2, -0.05, 0.05), key=lambda bb: bb.min.X)
    assert (a.max.X, b.min.X) == pytest.approx((-P.pivot_d / 2, P.pivot_d / 2), abs=0.02)


# each straight edge: the way its arm runs from the pivot, and which side of the line is open for the pencil
EDGES = [((1, 0), (0, -1)), ((0, 1), (1, 0)), ((-1, 0), (0, 1)), ((0, -1), (-1, 0))]


@pytest.mark.parametrize("k", range(4))
def test_straight_edges_run_through_the_pivot(part, k):
    """Along each arm, a thin probe across the edge: the part stops exactly on the line through the pivot, from the
    hub out to the tip (on the bar, both sides of the seam)."""
    (dx, dy), (ox, oy) = EDGES[k]
    reach = P.bar_len if k == 0 else P.arm
    spots = (P.w + 1, (P.w + reach) / 2, reach - 1) + ((P.split_x - 1, P.split_x + 1) if k == 0 else ())
    for s in spots:
        if dx:  # runs along X: probe across Y
            (bb,) = pieces(part, dx * s - 0.05, dx * s + 0.05, -5, 5)
            edge = bb.min.Y if oy < 0 else bb.max.Y
        else:
            (bb,) = pieces(part, -5, 5, dy * s - 0.05, dy * s + 0.05)
            edge = bb.min.X if ox < 0 else bb.max.X
        assert edge == pytest.approx(0, abs=1e-3)


@pytest.mark.parametrize("n", P.radii_in)
def test_pencil_hole_is_its_number_of_inches_from_the_screw(part, n):
    """At the bottom, the throat's gap along the bar is centred so the hole is n inches from the pivot."""
    r = n * INCH
    x = P.hole_x(r)
    a, b = sorted(pieces(part, x - 6, x + 6, P.hole_off - 0.05, P.hole_off + 0.05), key=lambda bb: bb.min.X)
    assert b.min.X - a.max.X == pytest.approx(P.throat_d, abs=0.02)
    assert math.hypot((a.max.X + b.min.X) / 2, P.hole_off) == pytest.approx(r, abs=0.01)


def test_top_is_bevelled_along_the_straight_edge(part):
    """Like a ruler: at the top the bar starts a bevel's width in from the edge, at the bottom right on it."""
    x = (P.w + P.bar_len) / 2
    (top,) = pieces(part, x - 0.05, x + 0.05, -5, P.w / 2, z=P.t - 0.1)
    assert top.min.Y == pytest.approx(P.bevel - 0.1, abs=0.05)


def test_build_writes_orange_plates(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "render" / "iso.png").exists() and (tmp_path / "step" / "circle_jig.step").exists()
    s = slicers.active()
    for plate in plates(P):
        got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"{plate.name}{s.project_suffix}")}
        assert got == {name: P.filament for name, _ in plate.items}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
@pytest.mark.parametrize("plate", [pl.name for pl in plates(P)])
def test_slicer_prints_each_plate_in_one_filament(tmp_path, plate):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    project = tmp_path / "plates" / f"{plate}{s.project_suffix}"
    assert s.same_objects(project, s.roundtrip(project, tmp_path / "rt.3mf"))
    report = s.slice_report(project, tmp_path / "s.3mf")
    assert {f for layer in report["layers"] for f in layer[0]} == {P.filament}


def test_a_nail_or_pencil_pokes_through_every_hole(part):
    """The user, 2026-10-30: the hole "isn't big enough to actually poke a nail or pencil through". The throat at the
    bottom clears poke_d with room for holes printing a bit small."""
    assert P.throat_d >= P.poke_d + 0.5
    x = P.hole_x(P.radii[0])
    a, b = sorted(pieces(part, x - 8, x + 8, P.hole_off - 0.05, P.hole_off + 0.05), key=lambda bb: bb.min.X)
    assert b.min.X - a.max.X >= P.poke_d + 0.5
