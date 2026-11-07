"""The shelf: print rules, the U's, the speaker fit, the rails in the U's. Expectations from params."""
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.clash import find_clashes
from speaker_shelf.assembly import placed_parts, rail_boxes, speaker_box
from speaker_shelf.parts import shelf, shelf_body
from speaker_shelf.params import P, side_wall

R = P.rail / 2
MID = P.wall_h / 2 + 0.3  # probe height, clear of the floor


@pytest.fixture(scope="module")
def body():
    return shelf_body(P)


def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN,) * 3)


def _pieces(part, probe, axis):
    return sorted((s.bounding_box() for s in (part & probe).solids()), key=lambda b: getattr(b.min, axis))


def test_prints_flat_watertight_on_layers_no_supports():
    part = shelf(P)
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert [z for z, _ in downward_faces(part) if z > 0.01] == []


def test_side_walls_print_at_least_two_lines():
    assert side_wall(P) >= 2 * P.printer.nozzle


def test_nothing_clashes_rails_speaker_shelf():
    assert find_clashes(placed_parts(P)) == []


def test_too_big_a_rail_clashes():
    """The clash test can fail: a rail 0.5 mm fatter than the U runs into it."""
    assert find_clashes([("shelf", shelf_body(P))] + rail_boxes(P, extra=0.5)) != []


@pytest.mark.parametrize("side", [1, -1])
def test_u_is_the_fit_tested_size(body, side):
    """Across the U, front to back, at the middle of the rail: p.rail of air between the prongs."""
    x = side * (P.rail_gap / 2 + P.rail_deep / 2)
    pieces = _pieces(body, _box(x - 0.05, x + 0.05, -20, 20, MID, MID + 0.1), "Y")
    assert len(pieces) == 2
    assert pieces[1].min.Y - pieces[0].max.Y == pytest.approx(P.rail, abs=0.01)


def test_u_bottoms_are_the_rail_gap_apart(body):
    """Along x through the rails' line: the tray's side faces (the U bottoms) span exactly rail_gap."""
    pieces = _pieces(body, _box(-80, 80, -0.05, 0.05, MID, MID + 0.1), "X")
    assert pieces[0].min.X == pytest.approx(-P.rail_gap / 2, abs=0.01)
    assert pieces[-1].max.X == pytest.approx(P.rail_gap / 2, abs=0.01)


@pytest.mark.parametrize("side", [1, -1])
def test_prongs_reach_past_the_rail(body, side):
    reach = abs(body.bounding_box().max.X if side > 0 else body.bounding_box().min.X)
    assert reach == pytest.approx(P.rail_gap / 2 + P.rail_deep + P.prong_reach, abs=0.01)


@pytest.mark.parametrize("side", [1, -1])
def test_u_opens_outward(body, side):
    """Nothing closes the U on its outer side: a rail-sized box from the rail out to beyond the prongs is all air."""
    x0 = P.rail_gap / 2
    lane = _box(x0, x0 + 40, -R, R, -1, 30) if side > 0 else _box(-x0 - 40, -x0, -R, R, -1, 30)
    assert (body & lane).volume == pytest.approx(0, abs=1e-6)


def test_pocket_fits_the_speaker_with_clearance(body):
    across = _pieces(body, _box(-60, 60, -P.speaker_d / 3, -P.speaker_d / 3 + 0.1, MID, MID + 0.1), "X")
    assert across[1].min.X - across[0].max.X == pytest.approx(P.speaker_w + 2 * P.speaker_clear, abs=0.01)
    deep = _pieces(body, _box(-0.05, 0.05, -90, 90, MID, MID + 0.1), "Y")
    assert deep[1].min.Y - deep[0].max.Y == pytest.approx(P.speaker_d + 2 * P.speaker_clear, abs=0.01)


def test_speaker_centered_on_the_rails():
    c = speaker_box(P).bounding_box().center()
    assert (c.X, c.Y) == pytest.approx((0, 0), abs=1e-6)
