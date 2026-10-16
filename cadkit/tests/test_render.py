"""Shaded previews: the nearest surface wins (z-buffer), in its own color."""
import pytest
from build123d import Color

pytest.importorskip("numba")
from PIL import Image

from cadkit.render import render
from conftest import box

RED, BLUE = Color(0.9, 0.1, 0.1), Color(0.1, 0.1, 0.9)


def test_nearest_surface_wins_whatever_the_order(tmp_path):
    low, high = box(0, 0, 0, 40, 40, 2), box(10, 10, 2, 20, 20, 3)
    for name, items in (("a", [(high, BLUE), (low, RED)]), ("b", [(low, RED), (high, BLUE)])):
        path = tmp_path / f"{name}.png"
        render(items, path, view=(0, 0, 1), px=200)
        img = Image.open(path).convert("RGB")
        r, g, b = img.getpixel((100, 100))  # middle of the picture: the raised blue block
        assert b > 2 * r
        r, g, b = img.getpixel((100, 20))  # near the top edge: the red slab
        assert r > 2 * b


def test_background_shows_outside_the_part(tmp_path):
    path = tmp_path / "c.png"
    render([(box(0, 0, 0, 40, 10, 2), RED)], path, view=(0, 0, 1), px=200, bg=(0, 255, 0))
    assert Image.open(path).convert("RGB").getpixel((100, 5)) == (0, 255, 0)


def test_crop_trims_the_background_to_a_margin(tmp_path):
    """A long thin part cropped: the picture takes the part's 4:1 shape (plus margin), not a square."""
    path = tmp_path / "d.png"
    render([(box(0, 0, 0, 40, 10, 2), RED)], path, view=(0, 0, 1), px=200, crop=True)
    w, h = Image.open(path).size
    assert w == 200 and 0.25 * w < h < 0.35 * w
