"""The nose, mouth and whiskers, drawn: a smooth closed nose, and smooth strokes a line wide for the philtrum, the
lips, the mouth's opening (the tongue inside is white; no tooth) and three whiskers a side, the top ones running
out past the face. They replace everything traced in the muzzle zone and along the whiskers."""
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import make_interp_spline
from shapely.geometry import LineString, Polygon
from shapely.ops import substring, unary_union

from . import art as A
from . import ears as E
from .params import P, Params


def loop(points, step: float = 0.05) -> Polygon:
    """Smooth closed curve through the points: a periodic cubic spline in chord length."""
    pts = np.asarray(list(points) + [points[0]], float)
    u = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    t = np.linspace(0, u[-1], max(int(u[-1] / step), 8))
    return Polygon(make_interp_spline(u, pts, k=3, bc_type="periodic")(t)).buffer(0)


@dataclass
class Muzzle:
    nose: Polygon
    strokes: list  # mouth lines and whiskers, LineStrings
    whiskers: list  # the whiskers alone, each ending at its outer tip
    zone: Polygon  # everything traced in here goes
    erase: object  # the box and a band along each stroke


def shapes(p: Params = P) -> Muzzle:
    dy = E.drop(p, A.load(p))

    def moved(pts):
        return [(x, y - dy) for x, y in pts]

    nose = loop(moved(p.nose))
    mouth = [E.curve(moved(s)) for s in p.mouth]
    whiskers = [E.curve(moved(s)) for s in p.whiskers]
    zone = Polygon(moved(p.muzzle_zone))
    bands = [substring(q, 0, q.length - p.stroke_end_keep).buffer(p.whisker_erase, cap_style="flat")
             for q in mouth + whiskers]
    erase = unary_union([zone, *bands])
    return Muzzle(nose, mouth + whiskers, whiskers, zone, erase)
