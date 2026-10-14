from dataclasses import replace

import pytest
from build123d import Align, Box, Pos

from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import tie_ladder


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, P.max_bay_len]])
def test_every_ladder_printable(bays):
    for seg in L.segments(P, bays):
        assert printable_problems(tie_ladder.make(P, bays, seg)) == []


@pytest.mark.parametrize("p", [P, replace(P, rail_base_w=2.4, fit_slide=0.3)])
def test_ladder_gauge(p):
    """On a real tie: groove centerlines rail_ctc apart, each groove rail_base_w + fit_slide wide."""
    bays = [16 * INCH]
    seg = L.segments(p, bays)[1]
    lad = tie_ladder.make(p, bays, seg)
    t = next(t for t in L.ties(p, bays) if seg.x_start < t.x < seg.x_end and not t.lip and not t.long and not t.gap)
    x = t.x - seg.x_start
    z0 = p.tie_h + p.tie_plate_h + 0.1
    probe = Pos(x - 0.1, 0, z0) * Box(0.2, p.tie_l, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
    pieces = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 4, "two shoulders per rail"
    grooves = [(pieces[0].max.Y, pieces[1].min.Y), (pieces[2].max.Y, pieces[3].min.Y)]
    widths = [b - a for a, b in grooves]
    centres = [(a + b) / 2 for a, b in grooves]
    assert widths == pytest.approx([p.groove_w] * 2, abs=0.01)
    assert centres[1] - centres[0] == pytest.approx(p.rail_ctc, abs=0.01)


def test_flangeway_clear_for_deep_vintage_flanges():
    """Nothing inside the gauge, next to the rail head, rises within flange_depth_max of the rail top."""
    bays = [16 * INCH]
    seg = L.segments(P, bays)[1]
    lad = tie_ladder.make(P, bays, seg)
    z0 = P.rail_top - P.flange_depth_max
    for yc in P.rail_ys:
        inward = -1 if yc > 0 else 1
        y_head = yc + inward * P.rail_head_w / 2
        y0 = min(y_head, y_head + inward * 1.6) + P.tie_l / 2
        probe = Pos(0, y0, z0) * Box(seg.x_end - seg.x_start, 1.6, 2, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & probe).volume < 1e-9


# ---- solder gap at mid-bay ------------------------------------------------------------------------

def _seg_with(p, bays, x):
    return next(s for s in L.segments(p, bays) if s.x_start < x < s.x_end)


@pytest.mark.parametrize("b", [P.min_bay_len, 16 * INCH, 76 * 5.5, P.max_bay_len])
def test_gap_runs_post_to_post_nearest_mid_bay(b):
    """The gap ties are all the plain ties between two neighbouring handrail-post ties, the pair nearest mid-bay."""
    ties = [t for t in L.ties(P, [b]) if 0 < t.x < b]
    k = [i for i, t in enumerate(ties) if t.gap]
    assert len(k) == P.long_tie_every - 1 and k == list(range(k[0], k[0] + len(k)))
    assert ties[k[0] - 1].long and ties[k[-1] + 1].long and not any(ties[i].long for i in k)
    centre = (ties[k[0]].x + ties[k[-1]].x) / 2
    assert abs(centre - b / 2) <= P.long_tie_every * L.bay_pitch(P, b) / 2 + 1e-6


def test_no_gap_when_disabled():
    assert not any(t.gap for t in L.ties(replace(P, solder_gap=False), [16 * INCH]))


def _gap_frame(p, b):
    bays = [b]
    seg = _seg_with(p, bays, b / 2)
    lad = Pos(seg.x_start, -p.tie_l / 2, 0) * tie_ladder.make(p, bays, seg)
    pb = L.bay_pitch(p, b)
    gap = [t.x for t in L.ties(p, bays) if t.gap]
    return lad, min(gap) - pb + p.tie_w / 2, max(gap) + pb - p.tie_w / 2, gap


@pytest.mark.parametrize("b", [16 * INCH, 76 * 5.5])
def test_notch_reaches_the_outside_of_each_rail(b):
    """Between the full ties either side of the gap, nothing from the rail groove's outer edge outward,
    top to bottom: the iron and the feeder touch the outside of the rail base."""
    lad, x0, x1, _ = _gap_frame(P, b)
    assert x1 - x0 >= 13.0
    g = P.groove_w / 2
    for y in P.rail_ys:
        s = 1 if y > 0 else -1  # room side (+y) keeps fake tie ends at the end
        lo = abs(y) + g + 0.05
        hi = P.tie_l / 2 - P.solder_room_stub - 0.2 if s > 0 else P.tie_l / 2 + 1
        assert hi - lo >= 4.0
        probe = Pos(x0 + 0.3, min(s * lo, s * hi), -1) * Box(x1 - x0 - 0.6, hi - lo, 10, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & probe).volume < 1e-6


@pytest.mark.parametrize("b", [16 * INCH, 76 * 5.5])
def test_runner_inner_part_continuous_and_center_ties_back(b):
    lad, x0, x1, gap = _gap_frame(P, b)
    for y in P.rail_ys:  # the inner part of each runner spans the gap (room side: cut once for the feeder passage)
        yi = y - (1 if y > 0 else -1) * (P.runner_w / 2 - 0.5)
        probe = Pos(x0 - 1, yi - 0.1, P.tie_h / 2) * Box(x1 - x0 + 2, 0.2, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
        assert len((lad & probe).solids()) == (2 if y > 0 else 1)
    for x in gap:  # the gap ties are back between the rails
        mid = Pos(x - 0.5, -2, 0.2) * Box(1.0, 4, P.tie_h - 0.4, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & mid).volume == pytest.approx(mid.volume, rel=1e-3)


def test_room_side_fake_tie_ends_are_attached():
    b = 16 * INCH
    bays = [b]
    seg = _seg_with(P, bays, b / 2)
    raw = tie_ladder.make(P, bays, seg)
    assert printable_problems(raw) == []  # stubs + bar join the ladder (one solid)
    lad = Pos(seg.x_start, -P.tie_l / 2, 0) * raw
    for t in (t for t in L.ties(P, bays) if t.gap):
        stub = Pos(t.x - 0.5, P.tie_l / 2 - P.solder_room_stub + 0.3, P.tie_h - 0.5) * Box(1, P.solder_room_stub - 0.6, 0.3,
                                                                                            align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & stub).volume == pytest.approx(stub.volume, rel=1e-3), "full-height tie end on the room side"
        wall = Pos(t.x - 0.5, -P.tie_l / 2, -1) * Box(1, P.tie_l / 2 - P.rail_ctc / 2 - P.runner_w / 2 - 0.2, 10,
                                                       align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & wall).volume < 1e-6, "wall side open"
    # the bar holding the stubs is on top (flush with the tie tops), not visible from below
    gap = sorted(t.x for t in L.ties(P, bays) if t.gap)
    between = (gap[0] + gap[1]) / 2
    y = P.tie_l / 2 - P.solder_room_stub / 2
    assert (lad & (Pos(between - 0.2, y - 0.2, P.tie_h - P.solder_bar_h + 0.1) * Box(0.4, 0.4, 0.4))).volume > 0
    assert (lad & (Pos(between - 0.2, y - 0.2, 0.0) * Box(0.4, 0.4, 0.4))).volume < 1e-6


# ---- two-color ladders: brown ties + runners, gray tie plates on top -------------------------------

@pytest.mark.parametrize("k", [0, 1])
def test_ladder_two_colors_one_change(k):
    bays = [16 * INCH]
    seg = L.segments(P, bays)[k]
    c = tie_ladder.make_colored(P, bays, seg)
    wood, steel = c.children
    whole = tie_ladder.make(P, bays, seg)
    assert len(wood.solids()) == 1
    assert (wood & steel).volume < 1e-3
    assert wood.volume + steel.volume == pytest.approx(whole.volume, rel=1e-4)
    assert wood.bounding_box().max.Z <= steel.bounding_box().min.Z + 1e-6
    assert wood.bounding_box().max.Z == pytest.approx(P.tie_h, abs=1e-6)


def test_room_feeder_passes_under_the_rail_to_the_center():
    """Between two gap ties, the room-side runner has a passage under the rail, so the room rail's feeder can go
    inward and drop between the panels; the ladder stays one piece."""
    b = 16 * INCH
    seg = _seg_with(P, [b], b / 2)
    raw = tie_ladder.make(P, [b], seg)
    assert printable_problems(raw) == []
    lad = Pos(seg.x_start, -P.tie_l / 2, 0) * raw
    gx = sorted(t.x for t in L.ties(P, [b]) if t.gap)
    xn, yr = (gx[0] + gx[1]) / 2, max(P.rail_ys)
    y0, y1 = yr - P.runner_w / 2 - 0.5, yr + P.groove_w / 2 + 0.5
    passage = Pos(xn - 0.5, y0, 0.1) * Box(1.0, y1 - y0, P.tie_h - 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (lad & passage).volume < 1e-6
