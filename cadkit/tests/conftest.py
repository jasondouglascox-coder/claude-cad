import pytest
from build123d import Align, Box, Color, Compound, Pos

MIN = (Align.MIN, Align.MIN, Align.MIN)
BROWN, GRAY = Color(0.43, 0.31, 0.22), Color(0.78, 0.79, 0.80)


def box(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


@pytest.fixture
def two_color():
    """A minimal two-color part: a brown slab with gray blocks on top (like ties with tie plates)."""
    def make(length=40.0, seam=2.4):
        wood = box(0, 0, 0, length, 10, seam)
        steel = box(2, 2, seam, 6, 6, 0.6) + box(length - 8, 2, seam, 6, 6, 0.6)
        wood.label, wood.color = "deck_wood", BROWN
        steel.label, steel.color = "deck_steel", GRAY
        return Compound(children=[wood, steel], label="deck")
    return make
