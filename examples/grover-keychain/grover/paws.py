"""The paws, drawn: each is a smooth closed outline (three toe lobes along its bottom) with a brown rim a line wide,
a white inside, and two brown toe lines rising from the cusps between the lobes. Raised in the top band, on white."""
from dataclasses import dataclass

from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import art as A
from . import ears as E
from . import vec as V
from .muzzle import loop
from .params import P, Params


@dataclass
class Paw:
    outer: Polygon
    brown: object  # rim + toe lines
    white: object


def shapes(p: Params = P) -> list[Paw]:
    dy = E.drop(p, A.load(p))
    out = []
    for outline, toes in zip(p.paw_outlines, p.paw_toes):
        outer = loop([(x, y - dy) for x, y in outline])
        lines = unary_union([E.curve([(x, y - dy) for x, y in t]).buffer(p.line_w / 2) for t in toes])
        brown = V.multi(unary_union([outer.difference(outer.buffer(-p.line_w)), lines.intersection(outer)]))
        out.append(Paw(outer, brown, V.multi(outer.difference(brown))))
    return out
