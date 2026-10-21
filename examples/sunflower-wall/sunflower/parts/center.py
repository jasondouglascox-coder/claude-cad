"""Seed head: a thin black floor out to the rim, brown diamond seeds on top in Vogel's spiral, doming up from the
rim (one flat color seam, black to brown)."""
from functools import lru_cache

from build123d import Align, Color, Compound, Cylinder, Face, Part, Pos, Wire, loft

from sunflower import layout
from sunflower.params import Params

BLACK, BROWN = Color(0.09, 0.08, 0.07), Color(0.36, 0.22, 0.10)


def _seed(s) -> Part:
    """A diamond seed: straight sides up to its shoulder, then a pyramid to a small flat top."""
    cell = s.cell
    cx = sum(x for x, _ in cell) / len(cell)
    cy = sum(y for _, y in cell) / len(cell)
    top = [(cx + (x - cx) * s.top_scale, cy + (y - cy) * s.top_scale, s.top) for x, y in cell]
    ring = lambda z: Face(Wire.make_polygon([(x, y, z) for x, y in cell], close=True))
    return loft([ring(0), ring(s.shoulder), Face(Wire.make_polygon(top, close=True))], ruled=True)


@lru_cache
def assembled(p: Params) -> Compound:
    """Centered on the flower axis, z = 0 at its underside."""
    body = Part(Cylinder(p.center_r, p.center_t, align=(Align.CENTER, Align.CENTER, Align.MIN)).solids())
    seeds = [Pos(0, 0, p.center_t) * _seed(s) for s in layout.seeds(p)]
    brown = Compound(children=seeds)
    body.label, body.color = "center_black", BLACK
    brown.label, brown.color = "center_brown", BROWN
    return Compound(children=[body, brown], label="center")
