import pytest
from build123d import Align, Box, Pos

from sunflower.params import P
from sunflower.parts import center, pin, quarter

MIN = (Align.MIN, Align.MIN, Align.MIN)


def probe(x, y, z, dx, dy, dz):
    """Thin box from (x, y, z): slice a feature with it and measure the pieces."""
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


@pytest.fixture(scope="session")
def back():
    return quarter.make(P, "back")


@pytest.fixture(scope="session")
def front():
    return quarter.make(P, "front")


@pytest.fixture(scope="session")
def head():
    return center.make(P)


@pytest.fixture(scope="session")
def snap():
    return pin.make(P)
