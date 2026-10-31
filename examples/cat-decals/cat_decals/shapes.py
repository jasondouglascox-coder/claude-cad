"""Drawing primitives on the 100-unit pose grid (y up): blobs, tapered strokes, cat heads."""
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union


def circle(x, y, r):
    return Point(x, y).buffer(r, quad_segs=24)


def ellipse(x, y, rx, ry, deg=0.0):
    return affinity.rotate(affinity.scale(circle(x, y, 1), rx, ry), deg)


def poly(*pts):
    return Polygon(pts)


def spline(pts, per=12):
    """Catmull-Rom through pts, ends held."""
    p = np.array(pts, float)
    p = np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1:i + 3]
        for t in np.linspace(0, 1, per, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(p[-2])
    return np.array(out)


def stroke(pts, r0, r1=None):
    """A smooth limb or tail through pts, its radius running r0 to r1 along its length."""
    r1 = r0 if r1 is None else r1
    s = spline(pts)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(s, axis=0).T))]
    r = r0 + (r1 - r0) * d / d[-1]
    disks = [circle(x, y, ri) for (x, y), ri in zip(s, r)]
    return unary_union([a.union(b).convex_hull for a, b in zip(disks, disks[1:])])


def head(x, y, s=1.0, tilt=0.0, facing=1):
    """A cat's head in profile looking along +x (facing=-1: -x): skull, muzzle, two pointed ears."""
    g = unary_union([
        circle(0, 0, 11),
        ellipse(7, -3.5, 6, 5.2),
        poly((-10.5, 3), (-2, 9.8), (-8, 18.5)),  # far ear
        poly((-3, 10), (7.5, 6), (3, 19)),  # near ear
    ])
    g = affinity.rotate(g, tilt, origin=(0, 0))
    g = affinity.scale(g, s * facing, s, origin=(0, 0))
    return affinity.translate(g, x, y)


def face(x, y, s=1.0, tilt=0.0):
    """A cat's head seen from the front (or behind): wide cheeks, two ears."""
    g = unary_union([
        ellipse(0, 0, 13, 11),
        poly((-13, 2), (-3, 9.5), (-11, 21)),
        poly((13, 2), (3, 9.5), (11, 21)),
    ])
    g = affinity.rotate(affinity.scale(g, s, s, origin=(0, 0)), tilt, origin=(0, 0))
    return affinity.translate(g, x, y)


def smooth(g, close=1.5, open_=1.0):
    """Blend the parts' joins (close the small notches), then round the sharp corners."""
    g = g.buffer(close, quad_segs=12).buffer(-close, quad_segs=12)
    return g.buffer(-open_, quad_segs=12).buffer(open_, quad_segs=12)


def groove(body, pts, r, gap, root=1):
    """Lay a tail along pts over body, cut free of it by a gap past pts[root] so it reads as its own part; it stays
    joined to the body where it grows from (pts[:root + 1])."""
    return body.difference(stroke(pts[root:], r + gap)).union(stroke(pts, r))
