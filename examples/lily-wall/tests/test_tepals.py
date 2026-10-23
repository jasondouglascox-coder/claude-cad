"""Tepals one at a time, and the colour plan: purple high, white low, a fade of whole layers between."""
import numpy as np
import pytest

from cadkit.checks import open_edges
from lily_wall import colour, tepals
from lily_wall.params import P


@pytest.mark.parametrize("k", [0, 1])
def test_tepal_rises_from_the_throat_and_recurves_to_the_bed(k):
    """Straight up out of the throat, level partway along, recurved down until its tip lands on the bed."""
    pts = tepals.grid(P, k)
    mid = pts[pts.shape[0] // 2]
    lean = np.degrees(np.arctan2(np.diff(mid[:, 0]), np.diff(mid[:, 2])))
    assert lean[0] < 5 and lean[-1] > 90 + 45  # upright at the foot, past 135 at the tip
    assert 0 <= mid[-1, 2] <= 1.5  # the tip comes down to the bed
    assert mid[:, 2].min() >= -1e-9
    assert np.argmax(mid[:, 2]) / len(mid) == pytest.approx(P.level, abs=0.1)


@pytest.mark.parametrize("k", [0, 1])
def test_tepal_edges_curl_below_its_midrib(k):
    pts = tepals.grid(P, k)
    peak = np.argmax(pts[pts.shape[0] // 2, :, 2])
    assert pts[0, peak, 2] < pts[pts.shape[0] // 2, peak, 2] - 3 and pts[-1, peak, 2] < pts[pts.shape[0] // 2, peak, 2] - 3


@pytest.mark.parametrize("k", [0, 1])
def test_tepal_is_a_closed_solid_on_the_bed(k):
    t = tepals.local(P, k)
    assert t.is_valid and len(t.solids()) == 1 and open_edges(t) == 0
    assert t.bounding_box().min.Z == pytest.approx(0, abs=1e-6)


def test_seam_on_a_layer_and_purple_from_near_the_throat_to_near_the_tip():
    """Along the inner tepal's midrib: white at the throat, purple from about a fifth of the way, white again from
    about three quarters (the photo)."""
    lo, hi = colour.band(P)
    assert P.printer.on_layer(lo) and P.printer.on_layer(hi) and hi - lo == pytest.approx(P.band)
    mid = tepals.grid(P, 1)[P.grid[1] // 2]
    t = np.linspace(0, 1, len(mid))
    purple = t[mid[:, 2] > colour.seam(P)]
    assert purple.min() == pytest.approx(0.18, abs=0.06) and purple.max() == pytest.approx(0.75, abs=0.06)


def test_the_fade_is_whole_layers_rising_from_white_to_purple():
    pattern = colour.pattern(P)
    assert len(pattern) == P.layers and set(pattern) <= {0, 1}
    quarters = [sum(q) / len(q) for q in np.array_split(pattern, 4)]
    assert quarters == sorted(quarters) and quarters[0] < 0.25 and quarters[-1] > 0.75
    seq = [0] + list(pattern) + [1]  # white below the fade, purple above
    assert colour.changes(P) == sum(a != b for a, b in zip(seq, seq[1:]))
    assert 15 <= colour.changes(P) <= 25
    assert "11" not in "".join(map(str, pattern[: P.layers // 4]))  # the first quarter never clumps purple
