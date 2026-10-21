from build123d import Align, Box, Pos

MIN = (Align.MIN, Align.MIN, Align.MIN)


def probe(x, y, z, dx, dy, dz):
    """Thin box from (x, y, z): slice a feature with it and measure the pieces."""
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)
