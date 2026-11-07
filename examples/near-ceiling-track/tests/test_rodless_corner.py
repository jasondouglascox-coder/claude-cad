"""Inside corners without the aluminum rods (2026-11-07): a support under every portal, and floor beams (and the end
anchors) wide enough along the track that each span's frame ends sit on them. The bridge corner keeps its rods."""
import math

import pytest
from build123d import Align, Box, Pos

from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain import plates
from hotrain.checks import printable_problems
from hotrain.params import P
from hotrain.parts import deep_bracket, floor_beam, portal_bracket
from hotrain.span_geom import span_geom

IN = C.inside_corner()
SUPPORTS = ("floor_beam", "portal")


@pytest.fixture(scope="module")
def items():
    return A.placed_parts(P, IN)


def test_inside_corners_have_no_rods_the_bridge_keeps_them(items):
    assert not IN.rods and C.bridge_corner().rods
    assert not any(n.startswith("rod_") for n, _ in items)
    assert not any("rod" in r[0] for r in C.layout_sheet(P, IN))
    assert any("rod" in r[0] for r in C.layout_sheet(P, C.bridge_corner()))


def test_a_support_under_every_portal():
    held = sorted([i for i, _ in IN.deep] + [i for i, _ in IN.portal])
    assert held == list(range(1, len(C.portals(P, IN)) - 1))


def test_every_bracket_is_on_the_layout_sheet():
    rows = [r[0] for r in C.layout_sheet(P, IN)]
    for i, wall in IN.deep + IN.portal:
        assert sum(f"P{i} (wall {wall})" in r for r in rows) == 1


def test_portal_brackets_sit_square_to_their_wall():
    """At the curve's ends the floor beam crosses the track square to the wall: one plane for beam and bracket."""
    ps = C.portals(P, IN)
    for i, wall in IN.portal:
        assert ps[i].heading == (0.0 if wall == "A" else 90.0)
        assert C.wall_offset(P, IN, ps[i]) == pytest.approx(P.track_offset)


def _probe(sp, yl: float, x: float, z0: float, z1: float, size: float = 1.0):
    """A small box in span sp's frame, around (x, yl), from z0 to z1."""
    return A.span_location(sp) * Pos(x, yl, z0) * Box(size, size, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def test_every_frame_end_bears_on_a_seat(items):
    """Just inside each end of each frame (but at the end anchors): the frame comes down to the tie underside, and
    a floor beam or portal bracket is right under it."""
    frames = {n: s for n, s in items if n.startswith("frame")}
    supports = [s for n, s in items if n.startswith(SUPPORTS)]
    spans = C.spans(P, IN)
    for sp in spans:
        for side, (_, yl, xs, ln) in zip(("inner", "outer"), A.frame_lines(P, sp.curved)):
            fr = frames[f"frame{sp.index}_{'inner' if yl > span_geom(P, sp.curved).yc else 'outer'}"]
            ends = [x for x, at_anchor in ((xs + 1.0, sp == spans[0]), (xs + ln - 1.0, sp == spans[-1])) if not at_anchor]
            for x in ends:
                assert (fr & _probe(sp, yl, x, 0.02, 0.3)).volume > 0, (sp.index, side, x)
                under = _probe(sp, yl, x, -0.3, -0.02)
                assert any((s & under).volume > 0 for s in supports), (sp.index, side, x)


def test_end_decks_rest_on_the_anchors(items):
    """At P0 and P7 the end deck's runner stubs sit on the anchor's top, as they did with the rods."""
    d = dict(items)
    spans = C.spans(P, IN)
    s = span_geom(P, False).s
    for sp, x, anchor in ((spans[0], 1.5, "anchor_in"), (spans[-1], s - 1.5, "anchor_out")):
        for u in P.rail_ys:
            assert (d[f"deck{sp.index}"] & _probe(sp, u, x, 0.02, 0.3, 5.0)).volume > 0, (sp.index, u)  # either side of
            assert (d[anchor] & _probe(sp, u, x, -0.3, -0.02, 5.0)).volume > 0, (sp.index, u)  # the pier slot


def test_rodless_supports_print_flat():
    for part in (floor_beam.make(P, rods=False), portal_bracket.make(P)):
        assert printable_problems(part) == []
        assert len(part.solids()) == 1


def test_rodless_beam_has_no_bores_and_seats_both_spans():
    beam = floor_beam.make(P, rods=False)
    assert beam.bounding_box().size.Z == pytest.approx(floor_beam.thickness(P, rods=False))
    assert floor_beam.thickness(P, rods=False) > P.fb_t + 2 * P.portal_gap  # reaches under both spans' ends
    assert beam.volume > floor_beam.make(P).volume * floor_beam.thickness(P, rods=False) / P.fb_t  # no bores


def test_inside_corner_kit_has_a_seat_beam_or_bracket_at_every_portal():
    names = {n for n, _ in plates.corner_kit(P, IN)}
    assert {"portal_bracket", "floor_beam_seat_18", "floor_beam_seat_36", "deep_bracket"} <= names
    assert "floor_beam" not in names
    counts = [n for n, _ in plates.corner_kit(P, IN)]
    assert counts.count("portal_bracket") == len(IN.portal)
    assert sum(n.startswith("floor_beam_seat") for n in counts) == len(IN.deep)
    assert counts.count("deep_bracket") == len(IN.deep)


def test_deep_brackets_at_18_degrees_reach_their_beams():
    ps = C.portals(P, IN)
    for i, wall in IN.deep:
        off = C.wall_offset(P, IN, ps[i])
        k = min(i, len(ps) - 1 - i) - 1  # 1 for P2/P5, 2 for P3/P4: degrees of turn from the wall
        assert off == pytest.approx(P.track_offset + P.curve_r * (1 - math.cos(math.radians(18 * k))), abs=0.01)


@pytest.mark.parametrize("move", [-0.5, 0.5])
def test_seat_beams_are_keyed_to_their_deep_brackets(items, move):
    """The rods used to hold each beam along its own length; now keys under it either side of its bracket do."""
    d = dict(items)
    ps = C.portals(P, IN)
    for i, wall in IN.deep:
        a = math.radians(ps[i].heading)
        slid = Pos(-move * math.sin(a), move * math.cos(a), 0) * d[f"floor_beam{i}"]
        assert (slid & d[f"deep{i}"]).volume > 1e-3, (i, move)


def test_portal_brackets_screw_on_at_the_deep_brackets_heights(items):
    """One set of screw marks for every corner bracket: the portal brackets reach as low as the deep brackets and
    put their screws at the same heights."""
    d = dict(items)
    for i, _ in IN.portal:
        assert d[f"portal{i}"].bounding_box().min.Z == pytest.approx(d["deep3"].bounding_box().min.Z, abs=1e-6)
    assert portal_bracket.screw_lines(P) == pytest.approx(
        tuple(s - floor_beam.bottom(P) for s in deep_bracket.SCREWS))
