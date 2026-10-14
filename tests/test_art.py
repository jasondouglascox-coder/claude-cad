"""The logo raster, classified and measured. Expectations come from params and the art itself."""
import numpy as np
import pytest

from grover import art as A
from grover.params import P


@pytest.fixture(scope="module")
def art():
    return A.load(P)


def test_scale_is_set_by_the_ribbon_width(art):
    ys, xs = np.where(art.valid)
    assert (xs.max() - xs.min()) / art.px_mm == pytest.approx(P.width, abs=0.05)


def test_ring_and_disc_are_concentric_circles(art):
    assert art.R > art.r > 0
    # the orange ring class fills an annulus between the disc circle and the outer circle
    y, x = np.mgrid[:art.cls.shape[0], :art.cls.shape[1]]
    d = np.hypot(x - art.cx, y - art.cy) / art.px_mm
    ring = art.fil == A.ORANGE
    inside = ring & (d < art.R - 1.0) & (d > art.r + 1.0)
    assert inside.sum() > 0.5 * ring.sum()
    assert (ring & (d > art.R)).sum() < 0.01 * ring.sum()


def test_every_pixel_maps_to_one_filament(art):
    assert set(np.unique(art.fil[art.valid])) <= {A.ORANGE, A.YELLOW, A.WHITE, A.BROWN}
    assert (art.fil[~art.valid] == 0).all()


def test_mm_frame_is_centered_on_the_ring(art):
    x, y = art.to_mm(np.array([art.cx]), np.array([art.cy]))
    assert x[0] == pytest.approx(0) and y[0] == pytest.approx(0)
    x, y = art.to_mm(np.array([art.cx]), np.array([art.cy - art.px_mm]))  # one mm up in the image
    assert y[0] == pytest.approx(1.0)
