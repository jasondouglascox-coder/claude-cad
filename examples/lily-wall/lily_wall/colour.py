"""White below, purple above, and between them the long fade: in a band round the seam, whole layers alternate
white and purple, the purple share rising from 0 to 1. A whole layer in one colour is one AMS swap per switch."""
from build123d import Align, Box, Pos

from cadkit.mesh import Mesh
from lily_wall import tepals
from lily_wall.params import Params

BIG = 600.0


def seam(p: Params) -> float:
    """seam_at of the way up the tepals (the inner ones, the taller)."""
    return p.seam_at * tepals.grid(p, 1)[..., 2].max()


def band(p: Params) -> tuple[float, float]:
    """The fade's bottom and top, on layer boundaries."""
    lo = p.printer.snap(seam(p) - p.band / 2)
    return lo, lo + p.band


def pattern(p: Params) -> list[int]:
    """Each fade layer's colour, bottom up (1 = purple): error-diffused, so the purple share rises smoothly and
    never clumps."""
    out, err = [], 0.0
    for i in range(p.layers):
        err += (i + 0.5) / p.layers
        c = 1 if err >= 0.5 else 0
        err -= c
        out.append(c)
    return out


def changes(p: Params) -> int:
    """AMS swaps the fade makes, from white below to purple above."""
    seq = [0] + pattern(p) + [1]
    return sum(a != b for a, b in zip(seq, seq[1:]))


def purple_region(p: Params) -> list:
    """Boxes covering every purple layer of the fade and everything above it."""
    lo, hi = band(p)
    h = p.printer.layer
    slab = lambda z0, z1: Pos(0, 0, z0) * Box(BIG, BIG, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    out = [slab(hi, BIG)]
    for i, c in enumerate(pattern(p)):
        if c:
            out.append(slab(lo + i * h, lo + (i + 1) * h))
    return out


def split(p: Params, m: Mesh) -> tuple[Mesh, Mesh]:
    """(white, purple): the mesh cut by layers, exactly."""
    region = Mesh.union([Mesh.from_shape(b) for b in purple_region(p)])
    return m - region, m & region
