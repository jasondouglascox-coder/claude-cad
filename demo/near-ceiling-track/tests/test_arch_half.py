import pytest
from build123d import Pos

from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import arch_half, keystone


@pytest.mark.parametrize("b", [P.min_bay_len, 16 * INCH, P.max_bay_len])
def test_arch_half_printable(b):
    assert printable_problems(arch_half.make(P, b)) == []


def test_arch_half_extent():
    bb = arch_half.make(P, 16 * INCH).bounding_box()
    assert bb.min.X == pytest.approx(0, abs=1e-6)
    assert bb.max.X == pytest.approx(8 * INCH)
    assert bb.max.Y == pytest.approx(P.pier_depth + P.tie_h)  # tabs poke up tie_h above the band
    assert bb.max.Z == pytest.approx(P.panel_t)


def test_keystone_printable_and_fits_socket_with_clearance():
    half = arch_half.make(P, 16 * INCH)
    key = keystone.make(P)
    assert printable_problems(key) == []
    h = 8 * INCH
    at_crown = Pos(h - P.key_len / 2, P.pier_depth - P.crown_depth / 2 - P.key_head / 2, 0) * key
    assert (half & at_crown).volume == pytest.approx(0, abs=1e-6)
