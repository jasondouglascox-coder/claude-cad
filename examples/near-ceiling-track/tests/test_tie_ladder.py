import math
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


@pytest.mark.parametrize("p", [P, replace(P, rail_base_w=2.4, fit_rail=0.3)])
def test_ladder_gauge(p):
    """On a real tie: grooves sunk in the wood, centerlines rail_ctc apart, each rail_base_w + fit_rail wide."""
    bays = [16 * INCH]
    seg = L.segments(p, bays)[1]
    lad = tie_ladder.make(p, bays, seg)
    t = next(t for t in L.ties(p, bays) if seg.x_start < t.x < seg.x_end and not t.long and not t.gap)
    x = t.x - seg.x_start
    probe = Pos(x - 0.1, 0, p.rail_base_z + 0.1) * Box(0.2, p.tie_l, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
    pieces = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 3, "the tie, cut by two grooves"
    grooves = [(pieces[0].max.Y, pieces[1].min.Y), (pieces[1].max.Y, pieces[2].min.Y)]
    widths = [b - a for a, b in grooves]
    centres = [(a + b) / 2 for a, b in grooves]
    assert widths == pytest.approx([p.groove_w] * 2, abs=0.01)
    assert centres[1] - centres[0] == pytest.approx(p.rail_ctc, abs=0.01)
    floor = Pos(x - 0.1, 0, p.rail_base_z - 0.1) * Box(0.2, p.tie_l, 0.05, align=(Align.MIN, Align.MIN, Align.MIN))
    assert len((lad & floor).solids()) == 1, "the groove floor is rail_sink down"


def test_rail_presses_in_and_clips_hold_it():
    """2026-11-04, after seven coupons: the base presses into a groove fit_rail narrower than nominal, sunk rail_sink
    in the brown (coupon 6, groove 2), and on every lip tie a gray clip each side reaches clip_reach over it, its
    underside rising clip_rise to a clip_tip-thick tip under a sloped lead-in (coupon 7, notch 1). The base edge
    goes under the clips' wall-side start; the clips print on whole layers."""
    assert P.rail_sink - P.rail_base_edge >= 0.1, "the base edge won't go under the clips"
    assert P.clip_h == pytest.approx(P.printer.layer * math.ceil((P.clip_rise + 2 * P.clip_tip) / P.printer.layer
                                                                 - 1e-6))
    assert 0 < P.clip_rise + P.clip_tip < P.clip_h
    assert P.fit_rail < 0 < P.clip_reach


def test_clips_hold_the_base_from_both_sides():
    """2026-11-05: the rail wouldn't press in past a clip on every tie (it slid in from the ends). Holding clips go back
    to coupon 7's: every clip_every-th tie, a tie long (clip_len), centred on it. Just above the tips, the base's way
    in between them is groove_w - 2 clip_reach wide."""
    bays = [16 * INCH]
    seg = L.segments(P, bays)[1]
    lad = tie_ladder.make(P, bays, seg)
    ties = [t for t in L.ties(P, bays) if seg.x_start < t.x < seg.x_end and not t.gap]
    assert P.clip_every == 4 and P.clip_len == P.tie_w
    z = P.tie_h + P.clip_rise + 0.05
    t = [t for t in ties if t.lip][1]
    probe = Pos(t.x - seg.x_start - 0.1, 0, z) * Box(0.2, P.tie_l, 0.05, align=(Align.MIN, Align.MIN, Align.MIN))
    pieces = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    assert len(pieces) == 4
    gaps = [pieces[1].min.Y - pieces[0].max.Y, pieces[3].min.Y - pieces[2].max.Y]
    assert gaps == pytest.approx([P.groove_w - 2 * P.clip_reach] * 2, abs=0.01)
    along = Pos(t.x - seg.x_start - P.tie_w, 0, z) * Box(2 * P.tie_w, P.tie_l, 0.05,
                                                         align=(Align.MIN, Align.MIN, Align.MIN))
    for s in (lad & along).solids():
        bb = s.bounding_box()
        assert bb.size.X == pytest.approx(P.clip_len, abs=0.01)
        assert bb.center().X == pytest.approx(t.x - seg.x_start, abs=0.01)


def test_spike_heads_on_the_other_ties_stand_clear_of_the_base():
    """2026-11-05: the ties between the holding clips get a gray spike head each side of each rail, spike_len long,
    centred, clip_h tall, spike_w wide, set spike_clear back from the base's edge: they read as nails but never touch
    the rail, so it presses in past them."""
    bays = [16 * INCH]
    seg = L.segments(P, bays)[1]
    lad = tie_ladder.make(P, bays, seg)
    ties = [t for t in L.ties(P, bays) if seg.x_start < t.x < seg.x_end and not t.long and not t.gap and not t.lip]
    t = ties[len(ties) // 2]
    x = t.x - seg.x_start
    probe = Pos(x - P.tie_w, 0, P.tie_h + 0.01) * Box(2 * P.tie_w, P.tie_l, P.clip_h + 1,
                                                       align=(Align.MIN, Align.MIN, Align.MIN))
    heads = sorted((s.bounding_box() for s in (lad & probe).solids()), key=lambda b: b.min.Y)
    assert len(heads) == 4
    for bb in heads:
        assert bb.size.X == pytest.approx(P.spike_len, abs=0.01)
        assert bb.center().X == pytest.approx(x, abs=0.01)
        assert bb.size.Y == pytest.approx(P.spike_w, abs=0.01)
        assert bb.max.Z == pytest.approx(P.tie_h + P.clip_h, abs=0.01)
    for y in P.rail_ys:
        clear = Pos(x - P.tie_w, y + P.tie_l / 2, P.tie_h + 0.01) * Box(
            2 * P.tie_w, P.rail_base_w + 2 * P.spike_clear - 0.02, P.clip_h + 1, align=(Align.MIN, Align.CENTER, Align.MIN))
        assert (lad & clear).volume < 1e-9


def test_groove_runs_out_through_the_jigsaw_tabs():
    """2026-11-05: the groove stopped 1 mm past the ladder's end, so the jigsaw tab's tip kept a nub of full tie
    height in the rail's path. It now runs out through the tabs: no wood over the groove floor anywhere on them."""
    bays = [16 * INCH, 14 * INCH]
    for seg in [s for s in L.segments(P, bays) if s.male_end]:
        lad = tie_ladder.make(P, bays, seg)
        x0 = seg.x_end - seg.x_start
        for y in P.rail_ys:
            path = Pos(x0 - 0.5, y + P.tie_l / 2, P.rail_base_z + 0.01) * Box(
                P.jig_len + 1, P.groove_w - 0.02, P.rail_sink + 1, align=(Align.MIN, Align.CENTER, Align.MIN))
            assert (lad & path).volume < 1e-9


def test_flangeway_clear_for_deep_vintage_flanges():
    """Nothing inside the gauge, next to the rail head, rises within flange_depth_max of the rail top, but the
    gauge-side clips: those stay clip_flange_clear below it (the user's wheels cleared coupon 7 with room to spare)."""
    bays = [16 * INCH]
    seg = L.segments(P, bays)[1]
    lad = tie_ladder.make(P, bays, seg)
    lips = [t.x - seg.x_start for t in L.ties(P, bays) if seg.x_start < t.x < seg.x_end and not t.gap]
    assert P.rail_top - (P.tie_h + P.clip_h) >= P.clip_flange_clear
    for z0, clips in ((P.rail_top - P.flange_depth_max, False), (P.rail_top - P.clip_flange_clear, True)):
        for yc in P.rail_ys:
            inward = -1 if yc > 0 else 1
            y_head = yc + inward * P.rail_head_w / 2
            y0 = min(y_head, y_head + inward * 1.6) + P.tie_l / 2
            probe = Pos(0, y0, z0) * Box(seg.x_end - seg.x_start, 1.6, 2, align=(Align.MIN, Align.MIN, Align.MIN))
            hit = lad & probe
            if clips:
                assert hit.volume < 1e-9
            else:  # only the clips and spike heads, on the ties
                assert all(any(abs(s.center().X - x) < P.clip_len for x in lips) for s in hit.solids())


@pytest.mark.parametrize("b", [16 * INCH, 76 * 5.5, P.max_bay_len])
def test_clips_rest_on_wood_and_tab_slots_open_to_the_sky(b):
    """The gray prints on the brown with no supports: every clip and spike head sits on wood, only a clip's rising
    underside leaning out over the groove. A tie over a panel tab's slot gets no clips, so the slot runs up through everything."""
    from cadkit.checks import unsupported
    bays = [b]
    mn = (Align.MIN, Align.MIN, Align.MIN)
    tl, tw = P.tab_len / 2 - 0.1, P.panel_t / 2 - 0.1
    for seg in L.segments(P, bays):
        body = tie_ladder.bodies(P, L.ties(P, bays), seg.x_start, seg.x_end, L.tab_xs(P, bays),
                                 seg.female_start, seg.male_end)
        wood, steel = body["wood"], body["steel"]
        probe = 0.1
        sliver = P.clip_reach * probe ** 2 / (2 * P.clip_rise) * P.clip_len
        clips = [s for s in steel.solids() if s.bounding_box().size.X > (P.clip_len + P.spike_len) / 2]
        assert unsupported(steel, wood, probe) == pytest.approx(len(clips) * sliver, rel=1e-3)
        for x in L.tab_xs(P, bays):
            if seg.x_start + P.tab_len < x < seg.x_end - P.tab_len:
                for y in P.rail_ys:
                    shaft = Pos(x - tl, y - tw, -1) * Box(2 * tl, 2 * tw, P.tie_h + 5, align=mn)
                    assert (shaft & (wood + steel)).volume < 1e-6


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
    for y in P.rail_ys:  # the inner part of each runner spans the gap: cut once by the feeder groove, whole under it
        yi = y - (1 if y > 0 else -1) * (P.runner_w / 2 - 0.5)
        for z, n in ((P.tie_h - 0.3, 2), (P.solder_feed_floor / 2, 1)):
            probe = Pos(x0 - 1, yi - 0.1, z - 0.1) * Box(x1 - x0 + 2, 0.2, 0.2, align=(Align.MIN, Align.MIN, Align.MIN))
            assert len((lad & probe).solids()) == n
    for x in gap:  # the gap ties are back between the rails
        mid = Pos(x - 0.5, -2, 0.2) * Box(1.0, 4, P.tie_h - 0.4, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & mid).volume == pytest.approx(mid.volume, rel=1e-3)


@pytest.mark.parametrize("b", [P.min_bay_len, 16 * INCH, 76 * 5.5, P.max_bay_len])
def test_feeder_groove_runs_across_both_rails_in_the_gaps_first_opening(b):
    """One groove straight across under both rails, between the full tie at the gap's start and the first gap tie,
    so the room rail's feeder ducks under both rails to the wall side and the rest of the gap is free to solder.
    A floor under it keeps the ladder in one piece."""
    lad, x0, _, gap = _gap_frame(P, b)
    assert printable_problems(Pos(-lad.bounding_box().min.X, -lad.bounding_box().min.Y, 0) * lad) == []  # one piece
    pb, hw, fw = L.bay_pitch(P, b), P.tie_w / 2, P.solder_feed_w / 2
    xn = min(gap) - pb / 2
    assert min(gap) - pb + hw < xn - fw and xn + fw < min(gap) - hw  # fits between the two ties
    assert xn - fw >= x0  # inside the notched stretch
    y_room = P.tie_l / 2 - P.solder_room_stub - 0.2  # room side: up to the fake tie ends
    clear = Pos(xn - fw + 0.05, -P.tie_l / 2 - 1, P.solder_feed_floor + 0.05) * Box(
        2 * fw - 0.1, y_room + P.tie_l / 2 + 1, P.tie_h, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (lad & clear).volume < 1e-6
    for y in P.rail_ys:  # floor under the runner's inner part (the outer part is notched away over the gap)
        y0 = y - P.runner_w / 2 if y > 0 else y - P.groove_w / 2
        floor = Pos(xn - fw + 0.05, y0 + 0.3, 0.05) * Box(
            2 * fw - 0.1, P.groove_w / 2 + P.runner_w / 2 - 0.6, P.solder_feed_floor - 0.1, align=(Align.MIN, Align.MIN, Align.MIN))
        assert (lad & floor).volume == pytest.approx(floor.volume, rel=1e-3)


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


# ---- two-color ladders: brown ties + runners, gray clips on top -------------------------------

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
