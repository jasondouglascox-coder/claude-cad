"""Layout math: quarters hide their seams, pins tie the rings together, seeds stay on the seed head."""
import math

import numpy as np
import pytest

from sunflower import layout
from sunflower.params import P, Params


def test_back_boundaries_run_through_back_gaps_under_front_petals():
    for a in layout.boundaries(P, "back"):
        assert min(abs((a - b + 180) % 360 - 180) for b in layout.back_angles(P)) == pytest.approx(P.pitch / 2)
        assert min(abs((a - f + 180) % 360 - 180) for f in layout.front_angles(P)) == pytest.approx(0)


def test_front_boundaries_run_through_front_gaps_offset_from_back():
    for a in layout.boundaries(P, "front"):
        assert min(abs((a - f + 180) % 360 - 180) for f in layout.front_angles(P)) == pytest.approx(P.pitch / 2)
    off = (layout.front_start(P) - layout.back_start(P)) % 90
    assert P.pitch <= off <= 90 - P.pitch  # not on top of a back seam


@pytest.mark.parametrize("layer", ["back", "front"])
def test_each_quarter_owns_the_same_number_of_petals(layer):
    angles = layout.back_angles(P) if layer == "back" else layout.front_angles(P)
    for a0 in layout.boundaries(P, layer):
        assert sum(layout.in_quarter(a, a0) for a in angles) == P.petals // 4


def test_every_quarter_gets_two_pins_and_every_pin_one_quarter_of_each_ring():
    pins = layout.pin_angles(P)
    assert len(pins) == 8
    for layer in ("back", "front"):
        for a0 in layout.boundaries(P, layer):
            assert sum(layout.in_quarter(a, a0) for a in pins) == 2
    for a in pins:  # well clear of every seam
        for b in layout.boundaries(P, "back") + layout.boundaries(P, "front"):
            assert abs((a - b + 180) % 360 - 180) * math.pi / 180 * P.pin_r > P.pin_t


def test_petal_count_must_split_into_identical_quarters():
    with pytest.raises(ValueError, match="multiple of 4"):
        layout.validate(Params(petals=18))


def test_petals_end_in_points_and_stay_inside_the_layer_height():
    for ring, top in ((P.back, P.back_t), (P.front, None)):
        assert layout.half_width(ring, ring.r1) == 0
        assert max(layout.half_width(ring, ring.r0 + k) for k in range(int(ring.r1 - ring.r0))) == \
            pytest.approx(ring.width / 2, rel=0.01)
        if top:
            assert max(z for _, z in ring.profile) < top  # back petals stay under the front ring


def test_front_petals_stay_under_the_seed_head_and_its_bevel():
    for k in range(200):
        r = P.front.r0 + k * (P.center_r - P.front.r0) / 200
        ceiling = P.front_t + max(0.0, r - P.center_rb)
        assert layout.midrib(P.front, r) < ceiling


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
    return [(np.array(s.cell), s) for s in layout.seeds(P)]


def test_no_bare_patch_on_the_seed_head(seeds):
    """Every spot of the head has a seed nearby (the first diamond seeds left the middle bare)."""
    cen = np.array([poly.mean(0) for poly, _ in seeds])
    lim = P.center_r - P.seed_edge - 3
    for x in np.arange(-lim, lim, 1.5):
        for y in np.arange(-lim, lim, 1.5):
            if math.hypot(x, y) < lim:
                assert np.min(np.hypot(*(cen - (x, y)).T)) <= 1.3 * P.seed_c, (x, y)  # a missing seed leaves ~1.8 c


def test_seed_tops_dome_like_a_real_head(seeds):
    tops = sorted((math.hypot(*poly.mean(0)), s.top) for poly, s in seeds)
    middle = [t for r, t in tops if r < 15]
    rim = [t for r, t in tops if r > P.center_r - P.seed_edge - 4]
    assert min(middle) - max(rim) >= P.seed_dome - 1.0
    for _, s in seeds:
        assert P.printer.on_layer(s.shoulder) and P.printer.on_layer(s.top) and s.top > s.shoulder > 0


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
        assert 2 * s.top_scale * layout.inradius(poly) >= 2 * P.printer.nozzle - 1e-9


def test_seeds_stay_on_the_head_and_keep_a_line_wide_gap(seeds):
    assert len(seeds) > 1000
    assert max(np.hypot(*poly.T).max() for poly, _ in seeds) <= P.center_r - 1.0
    cen = np.array([poly.mean(0) for poly, _ in seeds])
    order = np.argsort(cen[:, 0])
    for i, a in enumerate(order):  # sweep in x over neighbours
        for b in order[i + 1:]:
            if cen[b, 0] - cen[a, 0] > 8:
                break
            if np.linalg.norm(cen[b] - cen[a]) < 8:
                assert _gap(seeds[a][0], seeds[b][0]) >= P.printer.nozzle


def test_petal_veins_run_the_length():
    """Lengthwise grooves: across the petal the top rises and falls once per vein."""
    for ring in (P.back, P.front):
        r = (ring.r0 + ring.r1) / 2
        hw = layout.half_width(ring, r)
        zs = [layout.petal_top(P, ring, r, y, hw) for y in np.linspace(-0.95 * hw, 0.95 * hw, 400)]
        dips = sum(1 for a, b, c in zip(zs, zs[1:], zs[2:]) if b < a and b < c)
        assert dips >= P.petal_veins - 2
        bumps = np.array(zs) - [layout.petal_top(P, ring, r, y, hw, veins=False)
                                for y in np.linspace(-0.95 * hw, 0.95 * hw, 400)]
        assert bumps.min() == pytest.approx(-P.vein_depth, abs=0.05) and bumps.max() <= 1e-9


def test_pin_barbs_clear_the_throat_with_play_for_three_stacked_prints():
    y = layout.pin_y(P)
    assert y["barb"] - (P.back_t + P.front_t + P.throat) >= 0.25


def test_pin_arms_bend_well_inside_what_pla_takes():
    """Squeezing through the slot bends each arm as a cantilever from the end of the split: keep it under 2%."""
    assert layout.pin_strain(P) < 0.02
    assert layout.pin_strain(Params(pin_slot_len=7.0)) > 0.03  # the first design: it would have cracked
