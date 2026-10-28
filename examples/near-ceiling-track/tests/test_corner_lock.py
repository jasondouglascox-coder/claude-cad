"""The run deck locks to the corner deck ("the deck is what's adding stability to the whole unit", the user,
2026-10-28). At a corner end a run's ladder has a jigsaw tab, like the tabs between its ladders, and each corner's
end spans print as an end deck with runner stubs reaching the anchor and the matching sockets in them."""
from dataclasses import replace

import pytest
from build123d import Box, Pos

from cadkit.checks import printable_problems
from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain import layout as L
from hotrain import plates
from hotrain.params import INCH, P
from hotrain.parts import bow_deck, tie_ladder

D = replace(P, run_style="deck_truss")
B = 16 * INCH


def _run_frame(seg, ends):
    return tie_ladder.build(D, L.ties(D, [B], ends), seg.x_start, seg.x_end, L.tab_xs(D, [B]), seg.female_start,
                            seg.male_end, L.rod_tail_spans(D, [B], ends), seg.male_start)


def test_run_ladders_get_a_tab_at_each_corner_end():
    ends = (L.CORNER, L.CORNER)
    segs = L.segments(D, [B], ends)
    assert segs[0].male_start and not segs[0].female_start
    assert segs[-1].male_end
    assert not any(s.male_start for s in segs[1:])
    first, last = _run_frame(segs[0], ends), _run_frame(segs[-1], ends)
    assert first.bounding_box().min.X == pytest.approx(segs[0].x_start - D.jig_len, abs=0.02)
    assert last.bounding_box().max.X == pytest.approx(segs[-1].x_end + D.jig_len, abs=0.02)
    free = L.segments(D, [B], (L.FREE, L.FREE))
    assert not free[0].male_start and not free[-1].male_end


def test_end_deck_has_sockets_in_runner_stubs_at_the_anchor():
    wood = bow_deck.bodies(D, False, end=True)["wood"]
    assert len(wood.solids()) == 1
    assert wood.bounding_box().min.X == pytest.approx(0, abs=0.02)  # reaches the anchor (portal) line
    plain = bow_deck.bodies(D, False)["wood"]
    assert plain.bounding_box().min.X > 1  # the other spans still stop short of their floor beams

    def solid(x, y):
        return (wood & (Pos(x, y, D.tie_h / 2) * Box(0.2, 0.2, 0.2))).volume > 1e-6

    for y in D.rail_ys:
        assert not solid(D.jig_len / 2, y)  # the socket
        assert solid(D.jig_len / 2, y + (D.runner_w / 2 - 0.3))  # its walls
        assert solid(D.jig_len / 2, y - (D.runner_w / 2 - 0.3))
    assert printable_problems(bow_deck.make(D, False, end=True), D.printer) == []


@pytest.mark.parametrize("corner", [C.inside_corner(), C.bridge_corner()])
def test_each_corner_prints_two_end_decks(corner):
    names = [n for n, _ in plates.corner_kit(D, corner)]
    assert names.count("corner_deck_end") == 2
    spans = C.spans(D, corner)
    assert names.count("corner_deck_straight") == sum(not s.curved for s in spans) - 2


@pytest.mark.slow
@pytest.mark.parametrize("corner", [C.inside_corner(), C.bridge_corner()])
def test_run_tabs_seat_in_the_corner_sockets(corner):
    """Runs ending at the entry anchor and starting at the exit anchor: each tab sits in a socket (no clash, and
    the corner deck surrounds it on three sides), at both ends of the corner."""
    from hotrain import assembly
    items = A.placed_parts(D, corner)
    decks = [s for n, s in items if n.startswith("deck")]
    before = [(n, Pos(-B, 0, 0) * s) for n, s in assembly.placed_parts(D, [B], (L.FREE, L.CORNER))]
    pn = C.portals(D, corner)[-1]
    after = [(n, A.wall_b_frame(D, corner) * Pos(pn.y, 0, 0) * s)
             for n, s in assembly.placed_parts(D, [B], (L.CORNER, L.FREE))]
    for run in (before, after):
        ladders = [s for n, s in run if n.startswith("ladder")]
        for lad in ladders:
            for d in decks:
                assert (lad & d).volume < 1e-3
    # a probe across each tab's head, a little wider than the head, runs into the socket's walls on both sides
    exit_loc = A.wall_b_frame(D, corner) * Pos(pn.y, 0, 0)
    probe = lambda x, y: Pos(x, y, D.tie_h / 2) * Box(0.3, D.jig_head + 1.0, 0.5)
    tips = [probe(0.75 * D.jig_len, y) for y in D.rail_ys]  # entry: the run ends at the anchor, x = 0
    tips += [exit_loc * probe(-0.75 * D.jig_len, y) for y in D.rail_ys]  # exit: the run starts there
    for t in tips:
        assert sum((t & d).volume for d in decks) > 0
