"""The shelf: print rules, the clip sizes, the speaker fit, and the rails going in. Expectations from params."""
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.clash import find_clashes
from speaker_shelf.assembly import placed_parts, rail_boxes, speaker_box
from speaker_shelf.parts import hook_end_y, rail_outer_x, shelf, shelf_body
from speaker_shelf.params import P

R = P.rail / 2


@pytest.fixture(scope="module")
def body():
    return shelf_body(P)


def _box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN,) * 3)


def test_prints_flat_watertight_on_layers_no_supports():
    part = shelf(P)
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert [f for f in downward_faces(part) if f.center().Z > 0.01] == []


def test_nothing_clashes_rails_speaker_shelf():
    assert find_clashes(placed_parts(P)) == []


def test_too_big_a_rail_clashes():
    """The clash test can fail: a rail 0.5 mm fatter than the clip runs into the jaw and the hook."""
    fat = rail_boxes(P, extra=0.5)
    assert find_clashes([("shelf", shelf_body(P))] + fat) != []


@pytest.mark.parametrize("side", [1, -1])
def test_jaw_to_hook_is_the_fit_tested_size(body, side):
    """Along y through the clip, between the front jaw and the hook: exactly p.rail of air."""
    x = side * (rail_outer_x(P) - 1)
    probe = _box(x - 0.05, x + 0.05, -R - P.jaw_t - 1, R + 3, P.clip_h / 2, P.clip_h / 2 + 0.1)
    pieces = sorted((s.bounding_box() for s in (body & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 2
    assert pieces[1].min.Y - pieces[0].max.Y == pytest.approx(P.rail, abs=0.01)


@pytest.mark.parametrize("side", [1, -1])
def test_hook_reaches_behind_the_rail(body, side):
    xo = rail_outer_x(P)
    behind = _box(min(side * xo, side * (xo - P.rail)), max(side * xo, side * (xo - P.rail)), R, R + 0.5, 0, P.clip_h)
    covered = (body & behind).bounding_box()
    assert covered.size.X == pytest.approx(P.hook_depth, abs=0.01)


def test_pocket_fits_the_speaker_with_clearance(body):
    """A probe across the pocket at mid-wall height: the air is the speaker plus clearance both ways."""
    z = (P.floor_t + P.wall_h) / 2
    cy = -P.speaker_offset
    across = sorted((s.bounding_box() for s in (body & _box(-60, 60, cy - 0.05, cy + 0.05, z, z + 0.1)).solids()),
                    key=lambda b: b.min.X)
    inner = [b for b in across if abs(b.center().X) < P.rail_gap / 2]
    assert inner[1].min.X - inner[0].max.X == pytest.approx(P.speaker_w + 2 * P.speaker_clear, abs=0.01)
    deep = sorted((s.bounding_box() for s in (body & _box(-0.05, 0.05, -90, 30, z, z + 0.1)).solids()),
                  key=lambda b: b.min.Y)
    assert deep[1].min.Y - deep[0].max.Y == pytest.approx(P.speaker_d + 2 * P.speaker_clear, abs=0.01)


def test_rails_slide_in_from_the_back_touching_only_the_hooks(body):
    """Install: the shelf is pushed on from the front, so each rail travels from behind to y = 0.
    Along that path it meets nothing but the hooks (which the arms swing out of the way)."""
    for side in (1, -1):
        xo = rail_outer_x(P)
        x0, x1 = sorted((side * (xo - P.rail), side * xo))
        hit = body & _box(x0, x1, -R, 60, -1, 30)
        assert hit.volume > 0
        bb = hit.bounding_box()
        assert bb.min.Y >= R - 1e-6 and bb.max.Y <= hook_end_y(P) + 1e-6


def test_hooks_lead_in_at_45_degrees_or_shallower():
    assert P.hook_tip + P.hook_depth == pytest.approx(hook_end_y(P) - R)


def test_arm_bends_within_pla_strain_when_snapping_on():
    """Cantilever tip deflection hook_depth: strain 3 t d / (2 L^2) stays under 1% (PLA yields near 2-3%)."""
    assert 3 * P.arm_t * (P.hook_depth + P.arm_gap) / (2 * P.arm_free ** 2) < 0.01


def test_offset_load_cocks_the_clips():
    """A clip on a pole jams when the load sits further out than clip_h / (2 mu): 1.5x margin at mu."""
    assert P.speaker_offset > 1.5 * P.clip_h / (2 * P.mu)


def test_speaker_stays_centered_between_the_rails():
    assert speaker_box(P).bounding_box().center().X == pytest.approx(0, abs=1e-6)
    assert P.speaker_w / 2 + P.speaker_clear + P.wall < P.rail_gap / 2
