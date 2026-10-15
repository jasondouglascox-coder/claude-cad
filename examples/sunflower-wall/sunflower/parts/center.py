"""Seed head: a black body with a 45-degree bevel underneath, brown diamond seeds on top in Vogel's spiral (one color
change), and a socket for every pin: a throat the barbs snap over and a chamber with a 45-degree roof."""
import math
from functools import lru_cache

from build123d import Align, Box, Color, Compound, Cone, Face, Location, Part, Pos, Rectangle, Rot, Wire, extrude, loft

from sunflower import layout
from sunflower.params import Params

CHAMBER_SPARE = 0.2  # room each side of the barbs once they've snapped open
CHAMBER_EXTRA = 0.6  # headroom above the pin tip
ROOF_LEFT = 0.6  # flat strip left at the top of the 45-degree roof (a tiny bridge)
BLACK, BROWN = Color(0.09, 0.08, 0.07), Color(0.36, 0.22, 0.10)


def _seed(s) -> Part:
    """A diamond seed: straight sides up to its shoulder, then a pyramid to a small flat top."""
    cell = s.cell
    cx = sum(x for x, _ in cell) / len(cell)
    cy = sum(y for _, y in cell) / len(cell)
    top = [(cx + (x - cx) * s.top_scale, cy + (y - cy) * s.top_scale, s.top) for x, y in cell]
    ring = lambda z: Face(Wire.make_polygon([(x, y, z) for x, y in cell], close=True))
    return loft([ring(0), ring(s.shoulder), Face(Wire.make_polygon(top, close=True))], ruled=True)


def _layer(p: Params, z: float) -> float:
    return round(z / p.printer.layer) * p.printer.layer


def _socket(p: Params, a: float) -> list:
    mn = (Align.CENTER, Align.CENTER, Align.MIN)
    rad, tan = p.pin_w + p.fit, p.pin_t + p.fit
    ch = p.pin_w + 2 * p.pin_barb + p.fit + 2 * CHAMBER_SPARE
    h = _layer(p, p.pin_tip + CHAMBER_EXTRA)
    roof = _layer(p, (tan - ROOF_LEFT) / 2)
    at = Rot(0, 0, a) * Pos(p.pin_r, 0, 0)
    return [at * Pos(0, 0, -1) * Box(rad, tan, p.throat + 1, align=mn),
            at * Pos(0, 0, p.throat) * Box(ch, tan, h, align=mn),
            at * Pos(0, 0, p.throat + h) * extrude(Rectangle(ch, tan), roof, taper=45)]


@lru_cache
def assembled(p: Params) -> Compound:
    """Centered on the flower axis, z = 0 at its underside."""
    body = Part(Cone(p.center_rb, p.center_r, p.center_t, align=(Align.CENTER, Align.CENTER, Align.MIN)).solids())
    body = Part((body - [s for a in layout.pin_angles(p) for s in _socket(p, a)]).solids())
    seeds = [Pos(0, 0, p.center_t) * _seed(s) for s in layout.seeds(p)]
    brown = Compound(children=seeds)
    body.label, body.color = "center_black", BLACK
    brown.label, brown.color = "center_brown", BROWN
    return Compound(children=[body, brown], label="center")


def make(p: Params) -> Compound:
    """Print orientation: face up, in the +X +Y corner. Lower color first."""
    c = assembled(p)
    out = []
    for b in c.children:
        moved = Pos(p.center_r, p.center_r, 0) * b
        moved.label, moved.color = b.label, b.color
        out.append(moved)
    return Compound(children=out, label="center")


def place(p: Params) -> Location:
    return Pos(-p.center_r, -p.center_r, p.back_t + p.front_t)
