"""Geometry inside one bowstring span, in the span frame: origin at portal A, x along the chord A->B,
y to the left (toward the curve center), z up with 0 at the tie underside."""
import math
from dataclasses import dataclass

from hotrain.params import Params


@dataclass(frozen=True)
class SpanGeom:
    s: float  # chord length
    curved: bool
    r: float  # track radius (curved spans)
    h: float  # curve center height above the chord: center at (s/2, h)
    alpha: float  # span angle, radians (0 for straight)
    yc: float  # frame center line: centered on the track's stray from the chord
    d: float  # each end stops this far short of the portal (room for the floor beam)


def span_geom(p: Params, curved: bool) -> SpanGeom:
    s, r = p.bow_span, p.curve_r
    d = p.fb_t / 2 + p.portal_gap
    if not curved:
        return SpanGeom(s, False, r, 0.0, 0.0, 0.0, d)
    h = math.sqrt(r * r - s * s / 4)
    return SpanGeom(s, True, r, h, 2 * math.asin(s / 2 / r), -(r - h) / 2, d)


def track_at(g: SpanGeom, f: float) -> tuple[float, float, float]:
    """(x, y, heading rad) on the track at fraction f in [0, 1] of the span."""
    if not g.curved:
        return f * g.s, 0.0, 0.0
    t = -g.alpha / 2 + f * g.alpha
    return g.s / 2 + g.r * math.sin(t), g.h - g.r * math.cos(t), t


def offset_at(g: SpanGeom, f: float, u: float) -> tuple[float, float]:
    """Point u to the left of the track (toward the curve center) at fraction f."""
    x, y, a = track_at(g, f)
    return x - u * math.sin(a), y + u * math.cos(a)


def track_len(g: SpanGeom) -> float:
    return g.r * g.alpha if g.curved else g.s


def end_fractions(g: SpanGeom) -> tuple[float, float]:
    """Fractions where the printed span starts/ends (short of the portals by d)."""
    e = g.d / track_len(g)
    return e, 1 - e


def frame_x_range(g: SpanGeom, y_line: float) -> tuple[float, float]:
    """Where the line y = y_line meets the span's (shortened) end lines."""
    if not g.curved:
        return g.d, g.s - g.d
    f0, f1 = end_fractions(g)
    out = []
    for f in (f0, f1):  # radial line from the center through the track point at f
        x, y, _ = track_at(g, f)
        cx, cy = g.s / 2, g.h
        k = (y_line - cy) / (y - cy)
        out.append(cx + k * (x - cx))
    return out[0], out[1]
