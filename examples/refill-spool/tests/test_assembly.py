"""The assembled spool: the cap screws home without clashing, the coil fits, and every strap path is clear."""
from math import hypot

import pytest
from build123d import Align, Box, Pos, Rot

from cadkit.clash import find_clashes
from refill_spool.assembly import coil, placed_parts, strap_paths
from refill_spool.params import P, Params
from refill_spool.parts import engaged, play_per_flank, radial_box, ring


def test_cap_seats_on_the_barrel_without_clashing():
    parts = placed_parts(P)
    assert find_clashes(parts + [("coil", coil(P))]) == []
    (_, barrel), (_, cap) = parts
    assert cap.distance_to(barrel) == pytest.approx(0, abs=1e-3)
    assert cap.bounding_box().max.Z == pytest.approx(P.width, abs=1e-3)


def test_bore_runs_the_full_width():
    """Like the official spool, the AMS lite hub bears on a tube the whole way through, not two end rings."""
    a = 90 + 180 / P.spokes  # clear of the key, the spokes and the strap tracks
    whole = placed_parts(P)[0][1] + placed_parts(P)[1][1]
    probe = Rot(0, 0, a) * Pos(P.bore_d / 2 + 0.3, 0, -1) * Box(0.1, 0.1, P.width + 2, align=(Align.CENTER,
                                                                                            Align.CENTER, Align.MIN))
    bb = (whole & probe).bounding_box()
    assert (bb.min.Z, bb.max.Z) == (pytest.approx(0, abs=1e-3), pytest.approx(P.width, abs=1e-3))
    assert (whole & probe).volume == pytest.approx(0.01 * P.width, rel=1e-3)  # no gap along the way


def test_coil_sits_between_the_flanges_with_room_each_side():
    c = coil(P)
    bb = c.bounding_box()
    assert bb.min.Z - P.flange_t >= P.coil_side_clear - 1e-6
    assert P.barrel_top - bb.max.Z >= P.coil_side_clear - 1e-6
    assert bb.size.Z == pytest.approx(P.coil_w, abs=1e-3) and bb.size.X == pytest.approx(P.coil_d, abs=0.01)


def test_core_key_sits_in_the_cores_notch():
    """The key reaches into the core's wall, not past it: the coil's notch takes it with core_notch_clear round it."""
    assert P.barrel_d / 2 + P.key_h > P.core_d / 2 + 1.0
    assert P.barrel_d / 2 + P.key_h < P.core_od / 2
    (_, barrel), _ = placed_parts(P)
    key = barrel & radial_box(P.key_angle, P.barrel_d / 2 + 0.01, P.barrel_d / 2 + P.key_h + 1, P.key_w + 2,
                              P.key_len + 1, P.flange_t + 0.01)
    assert key.volume > 0
    assert key.distance_to(coil(P)) == pytest.approx(P.core_notch_clear, abs=0.02)


def test_threads_engage_with_play():
    """The bolt's crest reaches past the nut's crest over at least min_turns, so the cap only comes off by
    unscrewing, with min_play on each flank."""
    assert P.thread_depth - P.thread_clear >= P.thread_depth / 2
    assert engaged(P) >= P.min_turns * P.pitch
    assert play_per_flank(P) >= P.min_play


def bolt_points_in_nut(p):
    """Cap ridge mesh points (screwed home) that land inside the barrel half. Sampled with is_inside: OCC
    intersections of two swept ridges come back empty at random (cadkit.shapes.thread_gap)."""
    (_, barrel), (_, cap) = placed_parts(p)
    verts, _ = cap.tessellate(0.05, 0.3)
    lo, hi = p.barrel_top - p.thread_len, p.barrel_top - 0.01  # not the flange face resting on the barrel top
    pts = [v for v in verts if hypot(v.X, v.Y) > p.bolt_root + 0.05 and lo < v.Z < hi]
    assert len(pts) > 100
    return sum(barrel.is_inside(v) for v in pts[::2])


def test_screwed_home_the_ridges_clear():
    assert bolt_points_in_nut(P) == 0


def test_ridge_check_can_fail():
    """Same geometry with no flank play left: the cap's ridge runs into the nut."""
    assert bolt_points_in_nut(Params(thread_clear=-0.3)) > 0


def test_strap_paths_are_clear_with_the_cap_off():
    """Straps go on with the cap off (on, they'd stop it turning): each runs down a track under the core, out
    through the barrel half's flange, and back over the coil inside the rim."""
    (barrel_name, barrel), _ = placed_parts(P)
    things = [(barrel_name, barrel), ("coil", coil(P))]
    for k, path in enumerate(strap_paths(P)):
        hits = [(n, round((path & s).volume, 3)) for n, s in things if (path & s).volume > 1e-3]
        assert hits == [], f"strap {k}: {hits}"


@pytest.mark.parametrize("lift", [2.0, 10.0, 30.0, 70.0])
def test_coil_lifts_off_the_barrel(lift):
    """The coil slides straight off. Each tie's loop crosses the barrel half's outer face over the middle ring, so
    the user moves it round the ring as the coil comes off (the user's call: a gap in the ring would snag)."""
    (_, barrel), _ = placed_parts(P)
    assert round((Pos(0, 0, lift) * coil(P) & barrel).volume, 3) == 0
