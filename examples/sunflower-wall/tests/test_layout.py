"""Layout math at the flower's scale: petal shapes, and seeds that cover the head and dome up from its rim."""
import math

import numpy as np
import pytest

from sunflower import flower, layout

S = flower.params()


def test_petals_end_in_points_and_stay_inside_the_layer_height():
    for ring, top in ((S.back, S.back_t), (S.front, None)):
        assert layout.half_width(ring, ring.r1) == 0
        assert max(layout.half_width(ring, ring.r0 + k) for k in range(int(ring.r1 - ring.r0))) == \
            pytest.approx(ring.width / 2, rel=0.01)
        if top:
            assert max(z for _, z in ring.profile) < top  # back petals stay under the front ring


def _gap(a, b) -> float:
    """Distance between two convex polygons (0 if they overlap)."""
    def seg(p, q, r):
        d = q - p
        t = np.clip(np.dot(r - p, d) / np.dot(d, d), 0, 1)
        return np.linalg.norm(p + t * d - r)
    sep = False
    for P_, Q_ in ((a, b), (b, a)):
        for k in range(len(P_)):
            e = P_[(k + 1) % len(P_)] - P_[k]
            n = np.array([e[1], -e[0]])  # outward for counter-clockwise
            if np.all((Q_ - P_[k]) @ n > 0):
                sep = True
    if not sep:
        return 0.0
    return min(min(seg(P_[k], P_[(k + 1) % len(P_)], r) for k in range(len(P_)) for r in Q_)
               for P_, Q_ in ((a, b), (b, a)))


@pytest.fixture(scope="module")
def seeds():
    return [(np.array(s.cell), s) for s in layout.seeds(S)]


def test_no_bare_patch_on_the_seed_head(seeds):
    """Every spot of the head has a seed nearby (the first diamond seeds left the middle bare)."""
    cen = np.array([poly.mean(0) for poly, _ in seeds])
    lim = S.center_r - S.seed_edge - 3
    for x in np.arange(-lim, lim, 1.5):
        for y in np.arange(-lim, lim, 1.5):
            if math.hypot(x, y) < lim:
                assert np.min(np.hypot(*(cen - (x, y)).T)) <= 1.4 * S.seed_c, (x, y)  # a missing seed leaves ~1.8 c


def test_seed_tops_dome_like_a_real_head(seeds):
    lim = S.center_r - S.seed_edge
    tops = sorted((math.hypot(*poly.mean(0)), s.top) for poly, s in seeds)
    middle = [t for r, t in tops if r < 0.2 * lim]
    rim = [t for r, t in tops if r > 0.92 * lim]
    assert min(middle) - max(rim) >= S.seed_dome * (0.92 ** 2 - 0.2 ** 2) - 2 * S.printer.layer
    for _, s in seeds:
        assert S.printer.on_layer(s.shoulder) and S.printer.on_layer(s.top) and s.top > s.shoulder > 0


def test_seeds_are_diamonds_pointing_in_and_out(seeds):
    """Narrowed across the radius: each seed is longer toward the center than it is wide."""
    long = 0
    for poly, _ in seeds:
        c = poly.mean(0)
        ur = c / np.linalg.norm(c)
        ut = np.array([-ur[1], ur[0]])
        rel = poly - c
        long += np.ptp(rel @ ur) > np.ptp(rel @ ut)
    assert long / len(seeds) > 0.7


def test_seed_tops_print(seeds):
    for poly, s in seeds:
        assert 2 * s.top_scale * layout.inradius(poly) >= 2 * S.printer.nozzle - 1e-9


def test_seeds_stay_on_the_head_and_keep_a_line_wide_gap(seeds):
    assert max(np.hypot(*poly.T).max() for poly, _ in seeds) <= S.center_r - S.seed_edge + 1e-6
    cen = np.array([poly.mean(0) for poly, _ in seeds])
    order = np.argsort(cen[:, 0])
    for i, a in enumerate(order):  # sweep in x over neighbours
        for b in order[i + 1:]:
            if cen[b, 0] - cen[a, 0] > 8:
                break
            if np.linalg.norm(cen[b] - cen[a]) < 8:
                assert _gap(seeds[a][0], seeds[b][0]) >= S.printer.nozzle


def test_petal_veins_run_the_length():
    """Lengthwise grooves: across the petal the top rises and falls once per vein."""
    for ring in (S.back, S.front):
        r = (ring.r0 + ring.r1) / 2
        hw = layout.half_width(ring, r)
        ys = np.linspace(-0.95 * hw, 0.95 * hw, 400)
        bumps = np.array([layout.petal_top(S, ring, r, y, hw) - layout.petal_top(S, ring, r, y, hw, veins=False)
                          for y in ys])  # against the smooth top: the sides slope, so count dips in the grooves
        deep = bumps < -S.vein_depth / 2
        dips = sum(1 for a, b in zip(np.r_[False, deep], deep) if b and not a)  # stretches half a groove deep
        assert dips >= S.petal_veins - 2
        assert bumps.min() == pytest.approx(-S.vein_depth, abs=0.05) and bumps.max() <= 1e-9
