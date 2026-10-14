import math

import pytest
from build123d import Align, Box, Pos, Rot

from hotrain import corner_assembly as A
from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import bow_deck, bow_frame, deep_bracket, floor_beam, rod_anchor, rod_jig
from hotrain.span_geom import span_geom, track_at


@pytest.mark.parametrize("curved", [False, True])
def test_deck_printable(curved):
    assert printable_problems(bow_deck.make(P, curved)) == []


@pytest.mark.parametrize("curved", [False, True])
def test_frames_printable(curved):
    for _, _, _, ln in A.frame_lines(P, curved):
        assert printable_problems(bow_frame.make(P, ln)) == []


def test_curve_frames_inner_shorter_outer_longer():
    (k1, _, _, inner), (k2, _, _, outer) = A.frame_lines(P, True)
    (_, _, _, straight), _ = A.frame_lines(P, False)
    assert inner < straight < outer


def test_frame_crown_height():
    from dataclasses import replace
    P_ = replace(P, corner_style="bowstring")
    bb = bow_frame.make(P_, 160).bounding_box()
    assert bb.max.Y == pytest.approx(P_.rail_top + P_.bow_rise - bow_frame.u_bottom(P_), abs=0.2)  # print Y 0 = tab bottom


@pytest.mark.parametrize("part", ["floor_beam", "anchor", "deep", "jig"])
def test_support_parts_printable(part):
    s = {"floor_beam": lambda: floor_beam.make(P), "anchor": lambda: rod_anchor.make(P),
         "deep": lambda: deep_bracket.make(P, 149.6, 36), "jig": lambda: rod_jig.make(P)}[part]()
    assert printable_problems(s) == []


@pytest.mark.parametrize("curved", [False, True])
def test_curve_deck_gauge(curved):
    """At a tie mid-span: groove centerlines rail_ctc apart along the tie, each groove groove_w wide."""
    g = span_geom(P, curved)
    deck = bow_deck.build(P, curved)
    fr = bow_deck.tie_fracs(P, g)
    f = fr[len(fr) // 2 + 1]  # not a spike-lip tie
    x, y, a = track_at(g, f)
    z0 = P.tie_h + P.tie_plate_h + 0.1
    probe = Pos(x, y, z0) * Rot(0, 0, math.degrees(a)) * Box(0.2, 40, 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pieces = (deck & probe).solids()
    n = (-math.sin(a), math.cos(a))
    spans = sorted(((s.center().X - x) * n[0] + (s.center().Y - y) * n[1]) for s in pieces)
    assert len(spans) == 4, "two shoulders per rail"
    gap = lambda i: spans[i + 1] - spans[i] - P.shoulder_w
    assert [gap(0), gap(2)] == pytest.approx([P.groove_w] * 2, abs=0.02)
    centres = [(spans[0] + spans[1]) / 2, (spans[2] + spans[3]) / 2]
    assert centres[1] - centres[0] == pytest.approx(P.rail_ctc, abs=0.02)


@pytest.mark.slow
def test_every_corner_part_meshes_for_3mf(tmp_path):
    """Bambu Studio gets 3MF meshes; slivers from edge-to-edge unions make invalid meshes."""
    from build123d import Mesher
    from hotrain import corner_layout as CL, plates
    seen = {}
    for c in (CL.inside_corner(), CL.bridge_corner()):
        for n, s in plates.corner_kit(P, c):
            seen.setdefault(n, s)
    seen["rod_jig"] = rod_jig.make(P)
    for n, s in seen.items():
        m = Mesher()
        m.add_shape(s)
        m.write(str(tmp_path / f"{n}.3mf"))


def test_deep_bracket_two_screw_slots_and_solid_brace_joint():
    from build123d import Align, Box, Pos
    db = deep_bracket.make(P, 149.6, 36)
    d = deep_bracket.DEPTH
    # two separate screw slots in the flange
    hits = []
    for z10 in range(0, int(d * 10), 5):
        probe = Pos(0, z10 / 10, (P.bracket_t + P.flange_w) / 2) * Box(P.flange_t, 0.5, 0.5, align=(Align.MIN, Align.MIN, Align.MIN))
        hits.append((db & probe).volume < 1e-9)
    runs = sum(1 for a, b in zip([False] + hits, hits) if b and not a)
    assert runs == 2
    # the brace meets the flange over a real height, not at a point
    probe = Pos(P.flange_t + 0.5, 0, 0) * Box(0.5, d - P.bracket_member - 1, P.bracket_t, align=(Align.MIN, Align.MIN, Align.MIN))
    assert (db & probe).volume / (0.5 * P.bracket_t) >= 10.0


def _frame_solid_at(fr, x: float, z: float, depth: float) -> bool:
    """Is there frame material at length x, world height z (tie underside = 0), `depth` in from the outer face?"""
    y = z - bow_frame.u_bottom(P)
    return (fr & (Pos(x - 0.1, y - 0.1, depth - 0.1) * Box(0.2, 0.2, 0.2, align=(Align.MIN, Align.MIN, Align.MIN)))).volume > 1e-6


def test_frame_u_channel_hugs_the_ties():
    """Outer face solid gray down past the deck; two inward ledges above and below the tie band; tabs gone."""
    fr = bow_frame.make(P, 160)
    t, lg, fit = P.bow_frame_t, P.frame_ledge, P.fit_slide
    mid = t + lg / 2
    assert not _frame_solid_at(fr, 80, P.tie_h / 2, mid)  # groove the tie ends slide into
    assert _frame_solid_at(fr, 80, P.tie_h + fit + P.frame_ledge_hi / 2, mid)  # upper ledge
    assert _frame_solid_at(fr, 80, -fit - P.frame_ledge_lo / 2, mid)  # lower ledge
    for z in (-fit - P.frame_ledge_lo / 2, P.tie_h / 2, P.tie_h + 1):
        assert _frame_solid_at(fr, 80, z, t / 2)  # outer face covers the deck edge
    bb = fr.bounding_box()
    assert bb.min.Y == pytest.approx(0, abs=1e-6) and bb.min.Z == pytest.approx(0, abs=1e-6)
    assert bb.size.Z == pytest.approx(t + lg, abs=1e-6)
    assert bow_frame.u_bottom(P) == pytest.approx(-fit - P.frame_ledge_lo)


def test_lower_ledge_stops_short_of_the_floor_beams():
    fr = bow_frame.make(P, 160)
    z = -P.fit_slide - P.frame_ledge_lo / 2
    assert not _frame_solid_at(fr, 1.0, z, P.bow_frame_t + P.frame_ledge / 2)
    assert not _frame_solid_at(fr, 159.0, z, P.bow_frame_t + P.frame_ledge / 2)


def test_runner_mouth_is_a_gentle_snap():
    mouth = 2 * math.sqrt((P.rod_d / 2) ** 2 - (P.rod_mouth * P.rod_d) ** 2)
    assert 0.85 * P.rod_d <= mouth <= 0.92 * P.rod_d


def test_floor_beams_short_except_at_ceiling_drop():
    assert floor_beam.half_len(P, drop=False) <= P.track_offset - 2
    assert floor_beam.half_len(P, drop=True) > P.bow_frame_y + 8
    for drop in (False, True):
        assert printable_problems(floor_beam.make(P, drop)) == []


def _crossings(part, y: float) -> int:
    """Solid pieces cut by a thin horizontal probe at print height y."""
    bb = part.bounding_box()
    probe = Pos(bb.min.X - 1, y, bb.min.Z - 1) * Box(bb.size.X + 2, 0.2, bb.size.Z + 2, align=(Align.MIN, Align.MIN, Align.MIN))
    return len((part & probe).solids())


def test_pony_truss_top_height():
    fr = bow_frame.make(P, 160)
    assert P.corner_style == "pony"
    assert fr.bounding_box().max.Y == pytest.approx(P.rail_top + P.truss_rise - bow_frame.u_bottom(P), abs=0.2)


def test_pony_truss_web_members():
    """Mid-height cut: 2 inclined end posts + (n-1) verticals + (n-2) Pratt diagonals."""
    fr = bow_frame.make(P, 160)
    n = P.truss_panels
    mid = (P.tie_h + P.bow_chord_h + P.rail_top + P.truss_rise - P.truss_chord_w) / 2 - bow_frame.u_bottom(P)
    assert _crossings(fr, mid) == 2 + (n - 1) + (n - 2)


def test_pony_truss_top_chord_continuous():
    fr = bow_frame.make(P, 160)
    y = P.rail_top + P.truss_rise - P.truss_chord_w / 2 - bow_frame.u_bottom(P)
    assert _crossings(fr, y) == 1


def test_pratt_diagonals_slope_down_toward_center():
    """Left-half diagonal crossings move toward mid-span as the cut goes lower."""
    fr = bow_frame.make(P, 160)
    lo, hi = P.tie_h + P.bow_chord_h + 4 - bow_frame.u_bottom(P), P.rail_top + P.truss_rise - P.truss_chord_w - 4 - bow_frame.u_bottom(P)

    def left_diag_centers(y):
        bb = fr.bounding_box()
        probe = Pos(bb.min.X - 1, y, -1) * Box(bb.size.X + 2, 0.2, 10, align=(Align.MIN, Align.MIN, Align.MIN))
        xs = sorted(s.bounding_box().center().X for s in (fr & probe).solids())
        return xs[2]  # end post, first vertical, then the first diagonal

    assert left_diag_centers(lo) > left_diag_centers(hi)


def test_bowstring_style_still_available():
    from dataclasses import replace
    q = replace(P, corner_style="bowstring")
    bb = bow_frame.make(q, 160).bounding_box()
    assert bb.max.Y == pytest.approx(q.rail_top + q.bow_rise - bow_frame.u_bottom(q), abs=0.2)


# ---- two-color decks (wood ties, steel edge beams / runners / tie plates) -------------------------

@pytest.mark.parametrize("curved", [False, True])
def test_deck_wood_and_steel_bodies_partition_the_deck(curved):
    b = bow_deck.bodies(P, curved)
    whole = bow_deck.build(P, curved)
    assert (b["wood"] & b["steel"]).volume < 1e-3
    assert b["wood"].volume + b["steel"].volume == pytest.approx(whole.volume, rel=1e-4)
    assert len(b["wood"].solids()) == 1  # ties + rod runners: one brown piece, not a pile of ties


@pytest.mark.parametrize("curved", [False, True])
def test_deck_prints_with_one_color_change(curved):
    """Print orientation (ties up): every brown layer is below every gray layer."""
    c = bow_deck.make_colored(P, curved)
    wood, steel = c.children
    assert wood.bounding_box().max.Z <= steel.bounding_box().min.Z + 1e-6


@pytest.mark.parametrize("curved", [False, True])
def test_deck_ties_end_inside_the_truss_u(curved):
    """Ties reach the trusses' inner faces (less the slide fit), deep in the U, and no further."""
    from hotrain.span_geom import span_geom
    g = span_geom(P, curved)
    bb = bow_deck.bodies(P, curved)["wood"].bounding_box()
    inner = P.bow_frame_y - P.bow_frame_t / 2 - P.fit_slide
    assert bb.max.Y - g.yc == pytest.approx(inner, abs=1e-3)
    assert g.yc - bb.min.Y == pytest.approx(inner, abs=1e-3)


@pytest.mark.parametrize("curved", [False, True])
def test_frames_hug_the_deck_without_clashing(curved):
    deck = bow_deck.bodies(P, curved)["wood"]
    for kind, yl, xs, ln in A.frame_lines(P, curved):
        fr = A.frame_location(P, curved, yl, xs, ln) * bow_frame.make(P, ln)
        assert (deck & fr).volume < 1e-3
        assert deck.distance_to(fr) <= P.fit_slide + 1e-3


def test_colored_deck_matches_print_part_and_colors():
    from hotrain import room
    c = bow_deck.make_colored(P, True)
    assert [ch.label for ch in c.children] == ["corner_deck_curve_wood", "corner_deck_curve_steel"]
    assert tuple(c.children[0].color) == pytest.approx(tuple(room.TIE_BROWN))
    assert tuple(c.children[1].color) == pytest.approx(tuple(room.IRON))
    a, b = c.bounding_box(), bow_deck.make(P, True).bounding_box()
    for v, w in ((a.min, b.min), (a.max, b.max)):
        assert (v.X, v.Y, v.Z) == pytest.approx((w.X, w.Y, w.Z), abs=1e-6)


# ---- bus wire hook --------------------------------------------------------------------------------

def test_bus_hook_on_wall_side():
    """u is measured left of the track = toward the curve center = the room; the walls are at -u."""
    assert floor_beam.bus_u(P) < -P.rod_y
    assert floor_beam.bus_u(P) - 5 > -floor_beam.half_len(P)  # hook stays on the beam
