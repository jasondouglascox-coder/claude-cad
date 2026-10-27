from dataclasses import replace

import pytest

from hotrain import assembly
from hotrain import layout as L
from hotrain.params import INCH, P




@pytest.fixture(scope="module")
def parts():
    return dict(assembly.placed_parts(P, [16 * INCH]))


def test_part_count(parts):
    posts = len(L.post_us(P, 16 * INCH))
    segs = len(L.segments(P, [16 * INCH]))
    assert len(parts) == 4 + 2 + 2 * posts + 2 + 4 + 2 * segs


def test_arch_halves_sit_under_rails(parts):
    for y in P.rail_ys:
        s = "room" if y > 0 else "wall"
        a = parts[f"bay0_{s}_arch_start"].bounding_box()
        b = parts[f"bay0_{s}_arch_end"].bounding_box()
        assert a.min.X == pytest.approx(0, abs=1e-6) and a.max.X == pytest.approx(8 * INCH)
        assert b.min.X == pytest.approx(8 * INCH) and b.max.X == pytest.approx(16 * INCH)
        for bb in (a, b):
            assert (bb.min.Y + bb.max.Y) / 2 == pytest.approx(y)
            assert bb.min.Z == pytest.approx(-P.pier_depth)


def test_bracket_flange_on_wall_and_top_under_ties(parts):
    bb = parts["bracket0"].bounding_box()
    assert bb.min.Y == pytest.approx(-P.track_offset)
    assert bb.max.Z == pytest.approx(0, abs=1e-6)
    assert bb.min.X == pytest.approx(-P.bracket_t / 2)


def test_handrail_on_room_side(parts):
    bb = parts["handrail1"].bounding_box()
    assert (bb.min.Y + bb.max.Y) / 2 == pytest.approx(P.handrail_offset)
    assert bb.max.Z == pytest.approx(P.rail_top + P.handrail_h)


@pytest.mark.parametrize("p,bays", [
    (P, [16 * INCH]),
    (P, [16 * INCH, 14 * INCH, P.max_bay_len]),
    (P, [P.min_bay_len]),
    (replace(P, fit_slide=0.3, fit_snap=0.1, rail_base_w=2.4), [16 * INCH]),  # after a fit-test retune
    (replace(P, run_style="deck_truss"), [16 * INCH]),  # riveted panels, the mid-bay frame
])
@pytest.mark.slow
def test_no_interference(p, bays):
    assert assembly.clashes(p, bays) == []


def test_placed_parts_rejects_bad_bays():
    with pytest.raises(ValueError):
        assembly.placed_parts(P, [600.0])


@pytest.mark.slow
def test_clash_check_catches_tight_fits():
    tight = replace(P, fit_slide=-0.3)  # slots narrower than the panels
    clashes = assembly.find_clashes(assembly.placed_parts(tight, [16 * INCH]))
    names = {n for pair in clashes for n in pair[:2]}
    assert any(n.startswith("bracket") for n in names)
    assert any("cross_frame" in n for n in names)


@pytest.mark.slow
def test_bus_wires_run_clear_through_whole_run():
    """A 2-wire 16 AWG bundle along the wall clears every part, piers included, and rests on the fingers."""
    from build123d import Align, Box, Pos
    bays = [16 * INCH, 16 * INCH]
    x0, x1 = L.run_extent(P, bays)
    y0 = -(P.track_offset - P.flange_t) + P.finger_lip_w + 0.5  # just inside the cradle's wall lip
    bus = Pos(x0, y0, P.bus_floor) * Box(x1 - x0, 5.0, 2.4, align=(Align.MIN, Align.MIN, Align.MIN))
    items = assembly.placed_parts(P, bays) + [("bus", bus)]
    assert [c for c in assembly.find_clashes(items) if "bus" in c[:2]] == []


@pytest.mark.parametrize("style", ["arch", "deck_truss"])
@pytest.mark.parametrize("b", [16 * INCH, P.max_bay_len])
def test_feeder_path_clear_under_both_rails(style, b):
    """A 22 AWG feeder in the groove, from the room rail's notch under both rails and out past the wall-side
    tie ends, touches no part of the run."""
    from build123d import Align, Box, Pos
    p = replace(P, run_style=style)
    gap = [t.x for t in L.ties(p, [b]) if t.gap]
    xn, w = min(gap) - L.bay_pitch(p, b) / 2, p.solder_feed_w - 0.2
    y1 = p.tie_l / 2 - p.solder_room_stub - 0.2
    wire = Pos(xn - w / 2, -p.tie_l / 2 - 1, p.solder_feed_floor + 0.05) * Box(
        w, y1 + p.tie_l / 2 + 1, p.tie_h - p.solder_feed_floor - 0.1, align=(Align.MIN, Align.MIN, Align.MIN))
    items = assembly.placed_parts(p, [b]) + [("feeder", wire)]
    assert [c for c in assembly.find_clashes(items) if "feeder" in c[:2]] == []
