import itertools
from collections import Counter

import pytest

from hotrain import layout as L
from hotrain import plates
from hotrain.params import INCH, P


def test_nested_arch_pair_is_compact_with_clearance():
    pair = plates.nested_arch_pair(P, 16 * INCH)
    a, b = pair.solids()
    assert a.distance_to(b) >= plates.GAP - 0.05
    bb = pair.bounding_box()
    assert bb.size.Y < 2 * (P.pier_depth + P.tie_h) - 30  # really nests, not just stacked
    assert bb.min.Z == pytest.approx(0, abs=1e-6)


def check_plate(plate):
    shapes = [s for _, s in plate]
    for s in shapes:
        bb = s.bounding_box()
        assert bb.min.Z == pytest.approx(0, abs=1e-6)
        assert bb.min.X >= 0 and bb.min.Y >= 0 and bb.max.X <= P.bed and bb.max.Y <= P.bed
    for a, b in itertools.combinations(shapes, 2):
        ba, bb = a.bounding_box(), b.bounding_box()
        apart = (ba.max.X + plates.GAP <= bb.min.X or bb.max.X + plates.GAP <= ba.min.X
                 or ba.max.Y + plates.GAP <= bb.min.Y or bb.max.Y + plates.GAP <= ba.min.Y)
        assert apart or a.distance_to(b) >= plates.GAP - 0.05


@pytest.mark.slow
@pytest.mark.parametrize("bays", [[16 * INCH], [P.min_bay_len, P.max_bay_len]])
def test_every_plate_valid_and_every_part_printed(bays):
    from hotrain import build
    expected = Counter()
    for name, _, qty, _ in build.part_list(P, bays):
        expected[name] += qty
    got = Counter()
    for pl in plates.plates(P, bays):
        check_plate(pl.items)
        for name, _ in pl.items:
            got[name.split("#")[0]] += pl.qty
    assert got == expected


def test_standard_bay_kits_and_pooled_ladders():
    """Per-bay kits are single-color and dedupe across bays; all tie ladders share "ladders" plates."""
    one = plates.plates(P, [16 * INCH])
    gray = [pl for pl in one if not pl.name.startswith("ladders")]
    lad = [pl for pl in one if pl.name.startswith("ladders")]
    assert len(gray) == 3  # half span A, half span B (+ bracket), run ends
    assert all(not plates.is_two_color(s) for pl in gray for _, s in pl.items)
    n_lad = len(L.segments(P, [16 * INCH]))
    assert sum(len(pl.items) for pl in lad) == n_lad and len(lad) == 1
    many = plates.plates(P, [16 * INCH] * 6)
    gray = [pl for pl in many if not pl.name.startswith("ladders")]
    assert len(gray) <= 4
    assert sum(pl.qty for pl in gray) == 2 * 6 + 1
    lad = [pl for pl in many if pl.name.startswith("ladders")]
    assert sum(len(pl.items) for pl in lad) == len(L.segments(P, [16 * INCH] * 6))
    assert len(lad) <= (len(L.segments(P, [16 * INCH] * 6)) + 2) // 3  # at least ~3 ladders per plate


@pytest.mark.slow
def test_corner_plates_valid_and_complete():
    from hotrain import corner_layout as CL
    pls = plates.corner_plates(P)
    for pl in pls:
        check_plate(pl.items)
    for corner in (CL.inside_corner(), CL.bridge_corner()):
        expected = Counter(n for n, _ in plates.corner_kit(P, corner))
        got = Counter()
        for pl in pls:
            if pl.name.startswith(corner.name):
                got.update(n for n, _ in pl.items)
        assert got == expected
    assert any(pl.name == "rod_jig" for pl in pls)
