"""The assembled spool: the cap screws home without clashing, the coil fits, and every strap path is clear."""
from math import hypot

import pytest

from cadkit.clash import find_clashes
from refill_spool.assembly import coil, placed_parts, strap_paths
from refill_spool.params import P, Params
from refill_spool.parts import engaged, play_per_flank


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


def test_strap_paths_are_clear():
    """Each strap runs under the core in a barrel slot, out through both flanges, and back over the coil."""
    things = placed_parts(P) + [("coil", coil(P))]
    for k, path in enumerate(strap_paths(P)):
        hits = [(n, round((path & s).volume, 3)) for n, s in things if (path & s).volume > 1e-3]
        assert hits == [], f"strap {k}: {hits}"
