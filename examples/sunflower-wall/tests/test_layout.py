"""Layout math: quarters hide their seams, pins tie the rings together, seeds stay on the seed head."""
import math

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


def test_seeds_stay_on_the_head_and_never_touch():
    s = layout.seeds(P)
    assert len(s) > 1000
    for x, y, d, h in s:
        assert math.hypot(x, y) + d / 2 <= P.center_r
        assert P.printer.on_layer(h)
    pts = sorted(s)
    for i, (x, y, d, _) in enumerate(pts):  # sweep in x: neighbours closer than the biggest seed
        for x2, y2, d2, _ in pts[i + 1:]:
            if x2 - x > 4:
                break
            assert math.hypot(x2 - x, y2 - y) > (d + d2) / 2


def test_pin_barbs_clear_the_throat():
    y = layout.pin_y(P)
    assert y["barb"] > P.back_t + P.front_t + P.throat
