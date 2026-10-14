"""The ears, drawn: each ear's outer arch and inner line are smooth curves through points in params.

They replace the traced strokes there, whose outline had bumps where the art's fur, spurs and stroke ends met it.
Raster in, raster out at the art's resolution, like ink.py; regions.py swaps them in."""
from dataclasses import dataclass

import cv2
import numpy as np
from scipy.interpolate import make_interp_spline
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from . import art as A
from . import vec as V
from .params import P, Params


def curve(points, step: float = 0.02) -> LineString:
    """Smooth curve through the points: a natural cubic spline in chord length, sampled every `step` mm."""
    pts = np.asarray(points, float)
    u = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    t = np.linspace(0, u[-1], max(int(u[-1] / step), 2))
    return LineString(make_interp_spline(u, pts, k=3, bc_type="natural")(t))


def drop(p: Params, art: A.Art) -> float:
    """The figure's drop in mm, as regions.py moves the raster (whole pixels)."""
    return round(p.figure_drop * art.px_mm) / art.px_mm


def curves(p: Params = P) -> list[tuple[LineString, LineString]]:
    """[(arch, inner line)] per ear, moved down with the figure. The inner line starts on the arch (its first point
    snaps onto it), so its round end never pokes out of the ear's outline."""
    dy = drop(p, A.load(p))
    out = []
    for arch_pts, line_pts in zip(p.ear_arches, p.ear_lines):
        arch = curve([(x, y - dy) for x, y in arch_pts])
        line = [(x, y - dy) for x, y in line_pts]
        line[0] = arch.interpolate(arch.project(Point(line[0]))).coords[0]
        out.append((arch, curve(line)))
    return out


def _raster(g, art: A.Art, shape) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    for poly in V.multi(g).geoms:
        for ring, val in [(poly.exterior, 1)] + [(r, 0) for r in poly.interiors]:
            x, y = art.to_px(*np.asarray(ring.coords).T)
            cv2.fillPoly(m, [np.round(np.column_stack([x, y]) * 16).astype(np.int32)], val, shift=4)
    return m > 0


@dataclass
class Ears:
    ink: np.ndarray  # the drawn strokes, line_w wide
    erase: np.ndarray  # traced ink here goes
    outside: np.ndarray  # beyond the arches: no cat fill


def masks(p: Params, art: A.Art, shape) -> Ears:
    out, inn, line = p.ear_erase
    ink, erase, outside = [], [], []
    for arch, inner in curves(p):  # clockwise round the head, so the outside is on the arch's left
        ink += [arch.buffer(p.line_w / 2), inner.buffer(p.line_w / 2)]
        outside.append(arch.buffer(out, single_sided=True))
        erase += [outside[-1], arch.buffer(-inn, single_sided=True), inner.buffer(line)]
    return Ears(*(_raster(unary_union(g), art, shape) for g in (ink, erase, outside)))
