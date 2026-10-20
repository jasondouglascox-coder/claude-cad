"""Thin probes through a round part: measure solid pieces along a radius or across a tangent."""
import math

from build123d import Align, Box, Pos, Rot

MIN = (Align.MIN, Align.CENTER, Align.CENTER)


def radial(part, center, angle, z, r0=0.0, r1=110.0, w=0.1):
    """(r_in, r_out) of each solid piece a thin bar from r0 to r1 at `angle` degrees and height z cuts."""
    cx, cy = center
    bar = Pos(cx, cy, z) * Rot(0, 0, angle) * Pos(r0, 0, 0) * Box(r1 - r0, w, w, align=MIN)
    out = []
    for s in (part & bar).solids():
        rs = [math.hypot(v.X - cx, v.Y - cy) for v in s.vertices()]
        out.append((round(min(rs), 3), round(max(rs), 3)))
    return sorted(out)


def tangential_gap(part, center, angle, r, z, span=30.0, w=0.1):
    """Width of the gap a thin bar tangent at radius r, centered on `angle`, crosses at height z."""
    cx, cy = center
    bar = Pos(cx, cy, z) * Rot(0, 0, angle) * Pos(r, 0, 0) * Box(w, span, w)
    a = math.radians(angle)
    along = [sorted(((v.X - cx) * -math.sin(a) + (v.Y - cy) * math.cos(a)) for v in s.vertices())
             for s in (part & bar).solids()]
    lo = max(t[-1] for t in along if t[-1] <= 0.001)
    hi = min(t[0] for t in along if t[0] >= -0.001)
    return hi - lo


def radial_z(part, center, angle, r, z0=-1.0, z1=200.0, w=0.1):
    """(z_lo, z_hi) of each solid piece a thin vertical bar at radius r, `angle` degrees, cuts."""
    cx, cy = center
    a = math.radians(angle)
    bar = Pos(cx + r * math.cos(a), cy + r * math.sin(a), z0) * Box(w, w, z1 - z0, align=(Align.CENTER,
                                                                                         Align.CENTER, Align.MIN))
    return sorted((round(b.min.Z, 3), round(b.max.Z, 3)) for b in (s.bounding_box() for s in (part & bar).solids()))
