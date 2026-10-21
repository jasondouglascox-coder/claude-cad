"""Petals as printed (the flower's scale): never thinner than petal_min, vein grooves in the solid, and the front
petals' orange beads flush in their middle valleys, on yellow."""
import numpy as np
import pytest
from build123d import Pos

from conftest import probe
from sunflower import flower, layout
from sunflower.parts import petals

S = flower.params()


@pytest.mark.parametrize("layer", ["back", "front"])
def test_petal_is_never_thinner_than_the_minimum(layer):
    pet = petals.petal(S, layer)
    ring = S.back if layer == "back" else S.front
    for r in (ring.r0 + 3, (ring.r0 + ring.r1) / 2, ring.r1 - 3):
        hw = layout.half_width(ring, r)
        for y in (0, 0.9 * hw):
            col = pet & probe(r - 0.05, y - 0.05, 0, 0.1, 0.1, 30)
            assert col.bounding_box().max.Z >= S.petal_min - 1e-6


def test_printed_petal_keeps_its_vein_grooves():
    """The solid, not just the math: a spline through the cross sections once smoothed the grooves away."""
    pet = petals.petal(S, "front")
    r = (S.front.r0 + S.front.r1) / 2
    hw = layout.half_width(S.front, r)
    zs = []
    for y in np.linspace(-0.8 * hw, 0.8 * hw, 45):  # ~5 samples per groove, against the smooth top (sides slope)
        z = (pet & probe(r - 0.05, y - 0.05, 0, 0.1, 0.1, 30)).bounding_box().max.Z
        zs.append(z - layout.petal_top(S, S.front, r, y, hw, veins=False))
    deep = [z < -S.vein_depth / 2 for z in zs]
    dips = sum(1 for a, b in zip([False] + deep, deep) if b and not a)  # stretches half a groove deep
    assert dips >= S.petal_veins - 3  # the outer grooves sit past 0.8 of the half width


def test_middle_bead_runs_longest_the_outer_ones_shortest():
    """Some variety: every bead starts at the top of the arch, the middle one runs to bead_r's end, and each step
    out toward the edges ends sooner, the outermost bead_falloff of the length shorter."""
    r0, r1 = S.bead_r
    mid = S.bead_valleys[len(S.bead_valleys) // 2]
    ends = {k: layout.bead_end(S, k) for k in S.bead_valleys}
    assert ends[mid] == pytest.approx(r1)
    for k in S.bead_valleys:
        if k != mid:
            closer = k + (1 if k < mid else -1)
            assert ends[k] < ends[closer]
            assert ends[k] == pytest.approx(ends[2 * mid - k])  # the same each side
    out = S.bead_valleys[0]
    assert ends[out] == pytest.approx(r1 - (r1 - r0) * S.bead_falloff)


@pytest.mark.parametrize("k", [2, 4])
def test_bead_width_fades_in_then_tapers_out(k):
    r0, r1 = S.bead_r[0], layout.bead_end(S, k)
    w = lambda r: layout.bead_width(S, r, k)
    assert w(r0 - 0.1) == 0 and w(r1 + 0.1) == 0
    assert w(r0) == pytest.approx(S.bead_w_end) and w(r1) == pytest.approx(S.bead_w_end)
    assert w(r0 + S.bead_fade) == pytest.approx(S.bead_w)
    assert max(w(r0 + (r1 - r0) * i / 200) for i in range(201)) <= S.bead_w + 1e-9  # never wider


@pytest.fixture(scope="module")
def beads():
    return petals.beads(S)


def _bead_r_mid():
    r0, r1 = S.bead_r
    return r0 + S.bead_fade + (r1 - r0 - S.bead_fade) / 2


def test_one_orange_bead_down_each_middle_valley(beads):
    r0 = S.bead_r[0]
    assert len(beads.solids()) == len(S.bead_valleys)
    for s, k in zip(sorted(beads.solids(), key=lambda s: s.center().Y), S.bead_valleys):
        bb = s.bounding_box()
        assert bb.min.X == pytest.approx(r0, abs=0.05) and bb.max.X == pytest.approx(layout.bead_end(S, k), abs=0.05)
    r = _bead_r_mid()
    hw = layout.half_width(S.front, r)
    pieces = sorted((s.bounding_box() for s in (beads & probe(r - 0.05, -30, 0, 0.1, 60, 30)).solids()),
                    key=lambda b: b.center().Y)
    assert len(pieces) == len(S.bead_valleys)
    for b, k in zip(pieces, S.bead_valleys):
        assert b.center().Y == pytest.approx(layout.valley_u(S, k) * hw, abs=0.05)
        assert b.size.Y == pytest.approx(layout.bead_width(S, r, k), abs=0.05)


def test_beads_lie_flush_in_the_petal_top_on_yellow(beads):
    pet = petals.petal(S, "front")
    r = _bead_r_mid()
    hw = layout.half_width(S.front, r)
    y = layout.valley_u(S, S.bead_valleys[len(S.bead_valleys) // 2]) * hw
    b = (beads & probe(r - 0.05, y - 0.05, 0, 0.1, 0.1, 30)).bounding_box()
    top = layout.petal_top(S, S.front, r, y, hw)
    assert b.max.Z == pytest.approx(top, abs=0.05) and b.size.Z == pytest.approx(S.bead_t, abs=0.05)
    assert (beads - pet).volume == pytest.approx(0, abs=1e-3)  # inside the petal's shape: flush
    assert (Pos(0, 0, -0.1) * beads - pet).volume == pytest.approx(0, abs=1e-3)  # yellow right under every bead


def test_front_ring_has_the_beads_cut_out(beads):
    """The flower's yellow is built from front petals with the beads already cut out (fast), and nothing's lost."""
    cut = petals._front_petal_cut(S)
    assert cut.volume + beads.volume == pytest.approx(petals.petal(S, "front").volume, rel=1e-4)
    assert (cut & beads).volume == pytest.approx(0, abs=1e-3)
