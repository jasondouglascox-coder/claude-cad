"""The assembled spool: the cap screws home without clashing, the coil fits, and every strap path is clear."""
from math import hypot

import pytest
from build123d import Pos

from cadkit.clash import find_clashes
from refill_spool.assembly import coil, placed_parts, strap_paths
from refill_spool.params import P, Params
from refill_spool.parts import engaged, play_per_flank, ring


def test_cap_seats_on_the_barrel_without_clashing():
    parts = placed_parts(P)
    assert find_clashes(parts + [("coil", coil(P))]) == []
    (_, barrel), (_, cap) = parts
    assert cap.distance_to(barrel) == pytest.approx(0, abs=1e-3)
    assert cap.bounding_box().max.Z == pytest.approx(P.width, abs=1e-3)


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
    lo, hi = p.barrel_top - p.thread_len, p.barrel_top
    pts = [v for v in verts if hypot(v.X, v.Y) > p.bolt_root + 0.05 and lo < v.Z < hi]
    assert len(pts) > 100
    return sum(barrel.is_inside(v) for v in pts[::2])


def test_screwed_home_the_ridges_clear():
    assert bolt_points_in_nut(P) == 0


def test_ridge_check_can_fail():
    """Same geometry with no flank play left: the cap's ridge runs into the nut."""
    assert bolt_points_in_nut(Params(thread_clear=-0.3)) > 0


def test_strap_paths_are_clear_with_the_cap_off():
    """Straps go on with the cap off (on, they'd stop it turning): each runs under the core in a barrel slot, out
    through the barrel half's flange, and back over the coil inside the rim."""
    (barrel_name, barrel), _ = placed_parts(P)
    things = [(barrel_name, barrel), ("coil", coil(P))]
    for k, path in enumerate(strap_paths(P)):
        hits = [(n, round((path & s).volume, 3)) for n, s in things if (path & s).volume > 1e-3]
        assert hits == [], f"strap {k}: {hits}"


@pytest.mark.parametrize("lift", [2.0, 10.0, 30.0, 70.0])
def test_strapped_coil_lifts_off_the_barrel(lift):
    (_, barrel), _ = placed_parts(P)
    load = [coil(P)] + strap_paths(P)
    assert [round((Pos(0, 0, lift) * s & barrel).volume, 3) for s in load] == [0] * len(load)


def test_cap_lip_holds_the_barrel_top_in():
    """The barrel's strips are only joined at the bottom: screwed home, a lip on the cap wraps their top ends so
    the thread can't push them apart, lip_clear outside them."""
    (_, barrel), (_, cap) = placed_parts(P)
    lip = cap & (Pos(0, 0, P.barrel_top - P.lip_h) * ring(P.barrel_d / 2, P.barrel_d / 2 + 5, P.lip_h))
    bb = lip.bounding_box()
    assert bb.min.Z == pytest.approx(P.barrel_top - P.lip_h, abs=1e-3)
    assert min(hypot(v.X, v.Y) for v in lip.vertices()) == pytest.approx(P.barrel_d / 2 + P.lip_clear, abs=0.02)
    assert lip.distance_to(barrel) == pytest.approx(P.lip_clear, abs=0.02)
