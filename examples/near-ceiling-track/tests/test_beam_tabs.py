"""The user, 2026-11-09, after the reprinted inside corner: still not rigid ("the rail is really the only thing making
this whole thing ridgid"). Each floor beam (and portal bracket) gets a tab fb_tab_l long pushed up tight into each
deck's first gap, between its centre pad and its second tie, between the runners, and grows along the track to
carry them. The decks already printed are unchanged."""
import math

import pytest
from build123d import Box, Pos

from cadkit.checks import downward_faces, off_layer_z, printable_problems
from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain import plates
from hotrain.params import P
from hotrain.parts import bow_deck, floor_beam, portal_bracket
from hotrain.span_geom import span_geom

LAYER = P.printer.layer
# corner deck volumes (rodless) before the tabs: the decks the user has fought onto the rail must still fit
DECKS = {(False, ""): 13688.7156, (False, "in"): 13546.8998, (False, "out"): 13500.4184, (True, ""): 13612.4921}


def _on_layer(x: float) -> bool:
    return abs(x / LAYER - round(x / LAYER)) < 1e-6


@pytest.mark.parametrize("curved,end", list(DECKS))
def test_decks_are_unchanged(curved, end):
    assert bow_deck.build(P, curved, end, rods=False).volume == pytest.approx(DECKS[(curved, end)], abs=1e-3)


def test_seat_half_is_where_the_decks_pads_were_sized():
    assert floor_beam.seat_half(P, False) == pytest.approx(P.fb_t / 2 + P.portal_gap + P.frame_ledge_end - P.fb_seat_room)
    assert floor_beam.seat_half(P, True) == pytest.approx(P.fb_t / 2)


def test_first_gap_runs_from_the_pad_to_the_second_tie():
    a, b = floor_beam.first_gap(P)
    assert a == pytest.approx(floor_beam.seat_half(P, False) + P.deck_notch_room + 0.5)
    for curved in (False, True):
        g = span_geom(P, curved)
        from hotrain.span_geom import track_len
        second = bow_deck.tie_fracs(P, g)[1] * track_len(g) - P.tie_w / 2  # on the track's centre
        assert second - 0.2 < b <= second + 1e-9  # a curve's radial tie is nearer at the tab's inner end
    assert 1.5 < b - a < 2.5  # the user measured about 1.8 on the print


def test_tabs_are_tight_whole_layers_in_the_gap():
    a, b = floor_beam.first_gap(P)
    lo, hi = floor_beam.tab_span(P)
    assert lo >= a + P.fit_beam_tab - 1e-9 and hi <= b - P.fit_beam_tab + 1e-9
    assert lo - a < P.fit_beam_tab + LAYER and b - hi < P.fit_beam_tab + LAYER / 2  # no looser than the layers make it
    assert _on_layer(hi - lo) and _on_layer(2 * hi)  # its faces print on layer boundaries (the beam stands on end)


def test_rodless_beams_reach_to_the_tabs():
    assert floor_beam.thickness(P, False) == pytest.approx(2 * floor_beam.tab_span(P)[1])
    assert floor_beam.thickness(P, True) == pytest.approx(P.fb_t)  # the bridge's beams are unchanged


def _beam_point(part, u, z, s):
    """Is the seat beam from make() solid at (u left of the track, z above the tie underside, s along the track)?"""
    zb = floor_beam.bottom(P) - P.fb_key_h
    th = floor_beam.thickness(P, False)
    at = Pos(u + floor_beam.wall_end(P), z - zb, s + th / 2) * Box(0.1, 0.1, 0.1)
    return (part & at).volume > 1e-6


def test_tab_is_fb_tab_l_long_across_the_track_and_tie_high():
    part = floor_beam.make(P, rods=False, key_deg=18)
    lo, hi = floor_beam.tab_span(P)
    s, w = (lo + hi) / 2, P.fb_tab_l / 2
    for side in (1, -1):
        assert _beam_point(part, 0, P.tie_h - 0.1, side * s)
        assert not _beam_point(part, 0, P.tie_h + 0.1, side * s)
        assert _beam_point(part, w - 0.1, 1, side * s) and not _beam_point(part, w + 0.1, 1, side * s)
        assert _beam_point(part, -w + 0.1, 1, side * s) and not _beam_point(part, -w - 0.1, 1, side * s)
    assert P.fb_tab_l < P.rail_ctc - P.runner_w  # between the runners


def test_ridge_stays_under_the_decks_notches():
    """The ridge keeps to seat_half (with 45-degree ends) so it never reaches past the notch into the pad."""
    part = floor_beam.make(P, rods=False, key_deg=18)
    h, sh = P.fb_ridge_h, floor_beam.seat_half(P, False)
    assert _beam_point(part, 0, h - 0.1, sh - 0.05)
    assert not _beam_point(part, 0, 0.1, sh + h)
    assert sh + h < sh + P.deck_notch_room  # still inside the notch


@pytest.fixture(scope="module")
def inside():
    c = C.inside_corner()
    items = dict(A.placed_parts(P, c))
    decks = [items[f"deck{sp.index}"] for sp in C.spans(P, c)]
    seats = {i: s for n, s in items.items() for i in range(1, len(C.portals(P, c)) - 1)
             if n in (f"floor_beam{i}", f"portal{i}")}
    return c, decks, seats


def _along(pt, d):
    h = math.radians(pt.heading)
    return Pos(d * math.cos(h), d * math.sin(h), 0)


def test_tabs_lock_each_deck_along_the_track(inside):
    """Touching, not clashing; a deck pushed either way along the track by a hair hits a tab. In the model the tab
    is whole layers inside the gap (1.8 in 2.0-2.1); printed, the gap comes out about 1.8 (the user measured it), so
    the tab is a push fit there."""
    c, ds, seats = inside
    ps = C.portals(P, c)
    for i, seat in seats.items():
        for deck in (ds[i - 1], ds[i]):
            assert (deck & seat).volume < 1e-3, i
            for d in (P.fit_beam_tab + LAYER, -P.fit_beam_tab - LAYER):
                assert (_along(ps[i], d) * deck & seat).volume > 1e-3, (i, d)


def _kit_seats():
    return [(n, s) for n, s in plates.corner_kit(P, C.inside_corner()) if n.startswith(("floor_beam", "portal_bracket"))]


def test_tabbed_seats_print():
    """One solid, every flat face on a layer; the only real overhang is the far tab's underside (the beam stands on
    end, so the near tab is on the bed): the user chose it to keep the decks they have. Under ~8 mm^2: the short
    roofs over the truss ledges' clearance, the bracket's keyholes."""
    lo, hi = floor_beam.tab_span(P)
    for name, part in _kit_seats():
        assert printable_problems(part) == [] and len(part.solids()) == 1, name
        plate_top = P.bracket_t + round((hi - floor_beam.seat_half(P, False)) / LAYER) * LAYER
        assert off_layer_z(part, P.printer) in ([], [pytest.approx(plate_top)]), name  # bracket_t: as before
        big = [(z, a) for z, a in downward_faces(part) if a > 8]
        tab = [(z, a) for z, a in big if z == pytest.approx(2 * hi - (hi - lo))]
        assert len(tab) == 1 and tab[0][1] <= P.fb_tab_l * P.tie_h + 1e-3, (name, big)
        if name.startswith("floor_beam"):
            assert big == tab, (name, big)


def test_portal_bracket_marks_are_unchanged():
    """The flange (and its keyholes, placed from its far end) ends where it did: the screws already in the wall
    still fit. The plate thickens toward the beam's longer bed-side face instead of moving."""
    loc = portal_bracket.place(P, 0.0)
    part = loc * portal_bracket.make(P)
    end = part.bounding_box().max.X
    assert end == pytest.approx(-floor_beam.seat_half(P, False) + P.flange_w, abs=LAYER / 2)


# The review, 2026-11-09 (before printing): the tabs lock the decks to the seats along the track, so the deep
# brackets' stops shouldn't hold the seats to their marks within portal_gap; the 18-degree seats' room-side key hung
# past the beam's end; a lead-in on the tabs' tops helps a deck down onto two press-fit tabs.

def test_tabs_have_a_lead_in():
    part = floor_beam.make(P, rods=False, key_deg=18)
    lo, hi = floor_beam.tab_span(P)
    c = P.fb_tab_lead
    for side in (1, -1):
        assert _beam_point(part, 0, P.tie_h - 0.05, side * (lo + hi) / 2)
        for s in (lo + 0.05, hi - 0.05):
            assert not _beam_point(part, 0, P.tie_h - 0.05, side * s)
            assert _beam_point(part, 0, P.tie_h - c - 0.05, side * s)


@pytest.mark.parametrize("deg", [18, 36])
def test_keys_hang_wholly_under_the_beam(deg):
    from build123d import Rectangle
    prof = floor_beam.profile(P, rods=False, key_deg=deg)
    k = floor_beam.key_u(P, deg)
    z = floor_beam.bottom(P) + 2  # in the beam, above the key's own root
    for u in (k + P.fb_key_w - 0.05, -k - P.fb_key_w + 0.05):
        assert (prof & (Pos(u, z) * Rectangle(0.05, 0.05))).area > 1e-6, (deg, u)


@pytest.mark.parametrize("deg", [18, 36])
def test_rodless_deep_bracket_stops_leave_room_along_the_plate(deg):
    from build123d import Rectangle
    from hotrain.parts import deep_bracket
    w = 100.0
    prof = deep_bracket.profile(P, w, deg, rods=False)
    edge = deep_bracket.band(P, deg, rods=False) + P.deep_stop_room
    z = deep_bracket.DEPTH + 1.5
    at = lambda u: (prof & (Pos(u, z) * Rectangle(0.05, 0.05))).area > 1e-6
    for s in (1, -1):
        assert not at(w + s * (edge - 0.1)) and at(w + s * (edge + 0.1)), (deg, s)
    assert P.deep_stop_room >= 1.0
