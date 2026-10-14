import pytest

from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import handrail


@pytest.mark.parametrize("bays", [[16 * INCH], [16 * INCH, 14 * INCH, P.max_bay_len]])
def test_every_handrail_printable(bays):
    for pc in L.handrail_pieces(P, bays):
        assert printable_problems(handrail.make(P, pc)) == []


def test_handrail_height():
    pc = L.handrail_pieces(P, [16 * INCH])[1]
    bb = handrail.make(P, pc).bounding_box()
    assert bb.max.Y == pytest.approx(P.rail_top + P.handrail_h)
