"""The shapes everything is made of: tubes of vertical sections. A bell's are round above (an ellipse) and run in to
the bed below at 45 degrees or steeper, so nothing overhangs and the fill hides under the round. The green parts' and
the curled lobes' are domes: a half-oval standing on the bed, its round meeting the wall."""
import math

import numpy as np
import pytest

from cadkit.checks import open_edges, overhangs
from lily_of_the_valley import shapes


@pytest.mark.parametrize("r, zc, flat", [(2.5, 2.4, 1.0), (1.4, 3.5, 1.0), (12.0, 6.0, 0.85), (1.0, 0.3, 0.45)])
def test_a_section_stands_on_the_bed_and_never_overhangs(r, zc, flat):
    w, z, th = shapes.section(r, zc, flat)
    assert len(w) == shapes.section(2 * r, zc + 1, flat)[0].size  # every ring the same count, so rings line up
    assert z.min() == 0.0 and (z >= 0).all()
    assert 0.5 * np.sum(w * np.roll(z, -1) - np.roll(w, -1) * z) > 0  # counter-clockwise
    fill = np.isnan(th)
    assert fill.sum() > 0 and not np.isnan(th[0]) and np.isnan(th[-1])
    pts = np.stack([w, z], 1)
    seg = np.diff(np.vstack([pts, pts[:1]]), axis=0)
    under = seg[:, 0] > 1e-9  # running right along the bottom: the underside
    assert (np.abs(seg[under, 1]) >= np.abs(seg[under, 0]) - 1e-9)[np.abs(seg[under, 1]) > 1e-9].all()  # >= 45
    top = z.max()
    assert top == pytest.approx(zc + r * flat, rel=2e-3)  # round above (to the sampling)


def test_a_swept_tube_is_one_watertight_solid_with_no_overhang():
    path = shapes.bezier([(0, 0), (30, 0), (40, 20), (25, 35)], 50)
    m = shapes.sweep(path, np.linspace(2.5, 1.0, 50), np.linspace(2.4, 3.6, 50))
    assert m.is_valid and len(m.solids()) == 1 and open_edges(m) == 0
    assert m.bounding_box().min.Z == pytest.approx(0, abs=1e-9)
    assert overhangs(m) == []


@pytest.mark.parametrize("r, h", [(2.5, 4.0), (1.2, 4.0), (0.3, 0.4)])
def test_a_dome_is_a_half_oval_whose_round_meets_the_bed(r, h):
    """No flat band under the round: it comes down to the wall upright, as a stalk pressed to the wall would."""
    w, z = shapes.dome(r, h)
    assert len(w) == len(shapes.section(r, 2.0)[0])  # rings line up with the bells' sections
    assert z.min() == 0.0 and z.max() == pytest.approx(h)
    assert np.ptp(w[z == 0]) == pytest.approx(2 * r)
    assert 0.5 * np.sum(w * np.roll(z, -1) - np.roll(w, -1) * z) > 0  # counter-clockwise
    up = z > 0
    assert (w[up] / r) ** 2 + (z[up] / h) ** 2 == pytest.approx(np.ones(up.sum()))  # round all the way down


def test_a_swept_dome_is_one_watertight_solid_with_no_overhang():
    path = shapes.bezier([(0, 0), (30, 0), (40, 20), (25, 35)], 50)
    m = shapes.sweep_dome(path, np.linspace(2.5, 1.0, 50), 4.0)
    assert m.is_valid and len(m.solids()) == 1 and open_edges(m) == 0
    assert m.bounding_box().min.Z == pytest.approx(0, abs=1e-9) and m.bounding_box().max.Z == pytest.approx(4.0)
    assert overhangs(m) == []


def test_bezier_runs_through_its_end_points():
    c = shapes.bezier([(0, 0), (10, 5), (20, 0)], 11)
    assert c[0] == pytest.approx((0, 0)) and c[-1] == pytest.approx((20, 0)) and c[5] == pytest.approx((10, 2.5))
