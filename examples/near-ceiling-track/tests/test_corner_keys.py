"""The first corner prints (the user, 2026-11-08): the trusses didn't lock in (the U round the tie ends was loose),
the floor beams under the decks did nothing to locate them, the rod groove left under the rodless decks failed
prints, and the deck bowties were looser than the truss bowties (the keystones)."""
import math
from dataclasses import replace

import pytest
from build123d import Box, Pos

from hotrain import assembly
from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain import layout as L
from hotrain import plates
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import bow_deck, bow_frame, floor_beam, portal_bracket
from hotrain.span_geom import span_geom

D = replace(P, run_style="deck_truss")


def test_deck_bowties_fit_like_the_keystones():
    assert P.fit_jig == P.fit_key


def test_run_ladder_bowties_have_no_side_play():
    """Next ladders in a run: touching, not clashing; a hair sideways and the tab bites the socket's wall."""
    items = dict(assembly.placed_parts(D, [16 * INCH], (L.FREE, L.FREE)))
    lads = [items[k] for k in sorted(k for k in items if k.startswith("ladder"))]
    for a, b in zip(lads, lads[1:]):
        assert (a & b).volume < 1e-3
        assert (a & (Pos(0, 0.03, 0) * b)).volume > 1e-4


@pytest.fixture(scope="module", params=["inside", "bridge"])
def corner(request):
    c = C.inside_corner() if request.param == "inside" else C.bridge_corner()
    items = dict(A.placed_parts(D, c))
    decks = [items[f"deck{sp.index}"] for sp in C.spans(D, c)]
    seats = {i: s for n, s in items.items() for i in range(1, len(C.portals(D, c)) - 1)
             if n in (f"floor_beam{i}", f"portal{i}")}
    return c, decks, seats


def _along(pt, d: float):
    h = math.radians(pt.heading)
    return Pos(d * math.cos(h), d * math.sin(h), 0)


def _across(pt, d: float):
    h = math.radians(pt.heading)
    return Pos(-d * math.sin(h), d * math.cos(h), 0)


def test_corner_deck_bowties_have_no_play(corner):
    """Pushed together or pulled apart along the track by a hair, the decks' bowties bite: no slack left."""
    c, ds, _ = corner
    ps = C.portals(D, c)
    for i in range(1, len(ps) - 1):
        a, b = ds[i - 1], ds[i]
        assert (a & b).volume < 1e-3, i
        for d in (0.05, -0.05):
            assert (a & (_along(ps[i], d) * b)).volume > 1e-4, (i, d)


def test_every_deck_keys_onto_the_beam_under_each_of_its_portals(corner):
    """A V ridge on each beam's top sits in a notch under the decks' ends: touching, not clashing, and a deck moved
    a little across the track rides up the ridge."""
    c, ds, seats = corner
    ps = C.portals(D, c)
    for i, seat in seats.items():
        for deck in (ds[i - 1], ds[i]):
            assert (deck & seat).volume < 1e-3, i
            for d in (0.3, -0.3):
                assert (_across(ps[i], d) * deck & seat).volume > 1e-3, (i, d)


@pytest.mark.parametrize("make", [lambda: floor_beam.make(P), lambda: floor_beam.make(P, rods=False),
                                  lambda: floor_beam.make(P, rods=False, key_deg=18), lambda: portal_bracket.make(P)])
def test_beams_with_ridges_still_print(make):
    part = make()
    assert printable_problems(part) == [] and len(part.solids()) == 1


def test_ridge_is_45_degrees_on_the_beam_top():
    prof = floor_beam.profile(P, rods=False)
    h = P.fb_ridge_h
    solid = lambda u, z: (prof & (Pos(u, z) * _square(0.05))).area > 1e-6
    assert P.fb_ridge_w == pytest.approx(2 * h)  # 45-degree flanks: the deck's notch prints without a bridge
    assert solid(0, h - 0.1) and not solid(0, h + 0.1)
    assert solid(h / 2 - 0.1, h / 2 - 0.1) and not solid(h / 2 + 0.1, h / 2 + 0.1)


def _square(s):
    from build123d import Rectangle
    return Rectangle(s, s)


@pytest.mark.parametrize("curved", [False, True])
@pytest.mark.parametrize("rods", [True, False])
def test_decks_with_notches_still_print(curved, rods):
    for end in ("", "in", "out") if not curved else ("",):
        part = bow_deck.make(P, curved, end, rods=rods)
        assert printable_problems(part) == [], (end, rods)


@pytest.mark.parametrize("curved", [False, True])
def test_rodless_decks_have_no_rod_groove(curved):
    """Probe the tie undersides where the rod grooves were: solid without rods, open with them."""
    g = span_geom(P, curved)
    probe = lambda deck: sum((deck & (Pos(*_tie_point(g, f, u), 0.2) * Box(0.3, 0.3, 0.2))).volume
                             for f in bow_deck.tie_fracs(P, g)[2:6] for u in (P.rod_y, -P.rod_y))
    assert probe(bow_deck.bodies(P, curved, rods=False)["wood"]) > 0
    assert probe(bow_deck.bodies(P, curved)["wood"]) == pytest.approx(0, abs=1e-9)


def _tie_point(g, f, u):
    from hotrain.span_geom import offset_at
    return offset_at(g, f, u)[:2]


def test_inside_corner_kit_decks_are_rodless():
    kit = plates.corner_kit(P, C.inside_corner())
    vol = {n: s.children[0].volume for n, s in kit if n.startswith("corner_deck")}
    assert vol["corner_deck_curve"] == pytest.approx(bow_deck.bodies(P, True, rods=False)["wood"].volume, rel=1e-6)
    bridge = {n: s.children[0].volume for n, s in plates.corner_kit(P, C.bridge_corner()) if n.startswith("corner_deck")}
    assert bridge["corner_deck_curve"] == pytest.approx(bow_deck.bodies(P, True)["wood"].volume, rel=1e-6)


def test_frame_u_grips_the_ties():
    """The U is the tie's height plus fit_frame each side, and the tie ends reach to fit_frame off its web."""
    assert P.fit_frame <= P.fit_snap
    assert bow_frame.u_bottom(P) == pytest.approx(-P.fit_frame - P.frame_ledge_lo)
    for curved in (False, True):
        deck = bow_deck.bodies(P, curved)["wood"]
        for kind, yl, xs, ln in A.frame_lines(P, curved):
            fr = A.frame_location(P, curved, yl, xs, ln) * bow_frame.make(P, ln)
            assert (deck & fr).volume < 1e-3
            assert deck.distance_to(fr) <= P.fit_frame + 1e-3


# The user, 2026-11-08: "the cross beam should have grooves for the [part] the truss hangs down to sit in as well".
# The trusses' skirts now run their full length, and at each inside-corner floor beam or portal bracket they drop
# into a groove fit_tab wider than the web each side, its floor at the skirt's bottom.

def _probe(sp, yl, x, z0, z1, size=0.6):
    from build123d import Align
    return A.span_location(sp) * Pos(x, yl, z0) * Box(size, size, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def test_truss_skirts_run_to_their_ends():
    fr = bow_frame.make(P, 160)
    zb = bow_frame.u_bottom(P)
    for x in (0.5, 159.5):  # print Y is the height above the frame's bottom; the web is the first bow_frame_t of Z
        box = Pos(x, -zb / 2, P.bow_frame_t / 2) * Box(0.3, 0.3, 0.3)
        assert (fr & box).volume > 0, x


@pytest.fixture(scope="module")
def inside():
    c = C.inside_corner()
    return c, A.placed_parts(P, c)


def _frame_ends(c):
    """(span, frame name, frame line y, x just inside each end) for every frame end over a seat (not an anchor)."""
    spans = C.spans(P, c)
    for sp in spans:
        for _, yl, xs, ln in A.frame_lines(P, sp.curved):
            name = f"frame{sp.index}_{'inner' if yl > span_geom(P, sp.curved).yc else 'outer'}"
            for x, at_anchor in ((xs + 1.0, sp == spans[0]), (xs + ln - 1.0, sp == spans[-1])):
                if not at_anchor:
                    yield sp, name, yl, x


def test_truss_ends_sit_in_seat_grooves(inside):
    c, items = inside
    d = dict(items)
    seats = [s for n, s in items if n.startswith(("floor_beam", "portal"))]
    zb = bow_frame.u_bottom(P)
    for sp, name, yl, x in _frame_ends(c):
        fr = d[name]
        assert (fr & _probe(sp, yl, x, zb + 0.02, zb + 0.3)).volume > 0, (name, x)  # the skirt down in the groove
        assert any((s & _probe(sp, yl, x, zb - 0.3, zb - 0.02)).volume > 0 for s in seats), (name, x)  # its floor
        for dy in (0.3, -0.3):  # nudged across the track it runs into the groove's walls
            moved = A.span_location(sp) * Pos(0, dy, 0) * A.span_location(sp).inverse() * fr
            assert any((moved & s).volume > 1e-3 for s in seats), (name, x, dy)


def test_grooved_seats_still_print():
    for name, part in plates.corner_kit(P, C.inside_corner()):
        if name.startswith(("floor_beam", "portal_bracket")):
            assert printable_problems(part) == [] and len(part.solids()) == 1, name


def test_kit_seats_match_the_assembly():
    """Every seat in the kit is the part the assembly places, groove for groove (same name: same volume)."""
    c = C.inside_corner()
    kit = {}
    for n, s in plates.corner_kit(P, c):
        if n.startswith(("floor_beam", "portal_bracket")):
            kit.setdefault(n, set()).add(round(s.volume, 2))
    placed = {}
    for n, s in A.placed_parts(P, c):
        if n.startswith(("floor_beam", "portal")):
            placed.setdefault(s.label, set()).add(round(s.volume, 2))
    assert kit == placed
    assert all(len(v) == 1 for v in kit.values())


def test_decks_can_shift_along_their_beams(corner):
    """Review, 2026-11-08: the beams locate the decks across the track only. Along it, a deck (and its trusses)
    can move a little against the seats, so the chain of tight bowties needn't match the brackets' marks exactly."""
    c, ds, seats = corner
    ps = C.portals(D, c)
    room = min(P.deck_notch_room, P.fb_seat_room) - 0.1
    for i, seat in seats.items():
        for deck in (ds[i - 1], ds[i]):
            for d in (room, -room):
                assert (_along(ps[i], d) * deck & seat).volume < 1e-3, (i, d)


def test_truss_ledges_clear_the_seats_along_the_track(inside):
    c, items = inside
    seats = [s for n, s in items if n.startswith(("floor_beam", "portal"))]
    ps = C.portals(P, c)
    for n, fr in items:
        if n.startswith("frame"):
            sp = C.spans(P, c)[int(n[5])]
            for d in (P.fb_seat_room - 0.2, -(P.fb_seat_room - 0.2)):
                h = math.radians(math.degrees(math.atan2(sp.b.y - sp.a.y, sp.b.x - sp.a.x)))
                moved = Pos(d * math.cos(h), d * math.sin(h), 0) * fr
                assert all((moved & s).volume < 1e-3 for s in seats), (n, d)
