"""Drawing primitives on the 100-unit pose grid (y up): blobs, tapered strokes, cat heads."""
from dataclasses import dataclass
from math import atan2, cos, sin

import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box
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


def hull(*gs):
    """The smooth mass spanning several blobs: a body from chest to haunch, a neck from chest to head."""
    return unary_union(gs).convex_hull


def outline(pts):
    """A closed smooth outline through pts; a point given as (x, y, "sharp") is a corner (an ear tip)."""
    sharp = [i for i, q in enumerate(pts) if len(q) > 2]
    xy = [q[:2] for q in pts]
    if not sharp:
        n = len(xy)
        ring = spline(xy[-1:] + xy + xy[:2])[12:-12]  # periodic: wrap a point each way, drop their spans
        return Polygon(ring)
    i0 = sharp[0]
    xy = xy[i0:] + xy[:i0 + 1]  # start and end at a corner
    cuts = [i - i0 if i >= i0 else i - i0 + len(pts) for i in sharp] + [len(pts)]
    ring = np.vstack([spline(xy[a:b + 1])[:-1] for a, b in zip(cuts, cuts[1:])])
    return Polygon(ring).buffer(0)


# the head in profile looking along +x, skull centre at the origin: forehead down to a short muzzle, tall ears set back
PROFILE = [(12, -1.5), (10, 1.5), (7, 5), (5, 8), (3.5, 20.5, "sharp"), (-1.5, 10, "sharp"), (-6, 20, "sharp"), (-9.5, 6),
           (-10, 0), (-9, -5), (-3, -8.5), (4, -8), (8, -5.5), (11, -3.5)]
# the head seen from the front or behind: wide cheeks, ears at the corners
FACE = [(0, 9.5), (5, 10), (10.5, 19.5, "sharp"), (12.5, 7), (13, 0), (10, -7), (4, -10), (0, -10.5),
        (-4, -10), (-10, -7), (-13, 0), (-12.5, 7), (-10.5, 19.5, "sharp"), (-5, 10)]


def profile(x, y, s=1.0, tilt=0.0, facing=1):
    """A cat's head in profile looking along +x (facing=-1: -x)."""
    g = affinity.rotate(outline(PROFILE), tilt, origin=(0, 0))
    g = affinity.scale(g, s * facing, s, origin=(0, 0))
    return affinity.translate(g, x, y)


def blend(*gs, r=8.0):
    """Masses joined by curved fillets of radius r (a convex hull would join them with straight lines)."""
    return unary_union(gs).buffer(r, quad_segs=16).buffer(-r, quad_segs=16)


def ground(g, y=0.0):
    """Cut flat at y: the bottom of a sitting cat rests on the ground."""
    x0, _, x1, y1 = g.bounds
    return g.intersection(box(x0 - 1, y, x1 + 1, y1 + 1))


def yarn_ball(x, y, r, strand=()):
    """A ball of yarn: two curved slits across it, parallel like wound strands, stopping a rim short of its edge; a
    loose strand trails along strand (points)."""
    cx, cy, d = x - 1.6 * r, y - 1.6 * r, 1.6 * r * 2 ** 0.5  # the slits curve round a point off to the lower left
    reach = r - 2 - 0.33 * r  # slit centrelines stay this close to the middle, leaving the rim whole
    slits = []
    for off in (-0.33 * r, 0.33 * r):
        half = (reach ** 2 - off ** 2) ** 0.5 / (d + off)  # half the arc's angle
        a0 = atan2(y - cy, x - cx)
        slits.append(stroke([(cx + (d + off) * cos(a0 + t), cy + (d + off) * sin(a0 + t))
                             for t in (-half, 0, half)], 2.3))
    ball = circle(x, y, r).union(stroke(strand, 2.9)) if strand else circle(x, y, r)
    return Cut(ball, unary_union(slits))


def butterfly(x, y, s=1.0, tilt=0.0):
    """A butterfly seen from above, wings spread: big upper wings, smaller lower ones, a notch between them at each
    side (no antennae: too thin to cut)."""
    right = unary_union([ellipse(7, 6, 7, 4.3, 40), ellipse(5, -6, 4.8, 3.2, -50)])
    g = unary_union([right, affinity.scale(right, -1, 1, origin=(0, 0)), stroke([(0, -6), (0, 4.5)], 1.6),
                     circle(0, 5.5, 2)])
    g = affinity.rotate(affinity.scale(g, s, s, origin=(0, 0)), tilt, origin=(0, 0))
    return affinity.translate(g, x, y)


def fur(pts, r, h, every, side=1):
    """Tufts of bristling fur about h long every so often along the edge r out from the path pts (side 1: its left,
    -1: its right), uneven and swept back along the path like flames."""
    sp = spline(pts, per=40)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(sp, axis=0).T))]
    spikes = []
    for k, at in enumerate(np.arange(every / 2, d[-1] - every / 2, every)):
        i = int(np.searchsorted(d, at))
        t = sp[min(i + 1, len(sp) - 1)] - sp[max(i - 1, 0)]
        t = t / np.hypot(*t)
        n = side * np.array([-t[1], t[0]])
        p = sp[i]
        w = every * 0.6
        hk = h * (0.7 + 0.6 * ((k * 0.618) % 1))  # golden-ratio steps: uneven but never clumped
        spikes.append(Polygon([p + n * (r - 2) - t * w, p + n * (r - 2) + t * w, p + n * (r + hk) + t * hk * 0.9]))
    return unary_union(spikes)


def pieces(g):
    """The separate polygons of a shape."""
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def face(x, y, s=1.0, tilt=0.0):
    """A cat's head seen from the front (or behind)."""
    g = affinity.rotate(affinity.scale(outline(FACE), s, s, origin=(0, 0)), tilt, origin=(0, 0))
    return affinity.translate(g, x, y)


@dataclass(frozen=True)
class Cut:
    """A solid with deliberate gaps (yarn winding, a tail cut free of the body) taken out after smooth(), which
    would otherwise fill them."""
    solid: object
    gaps: object = None

    def __or__(self, other):
        o = other if isinstance(other, Cut) else Cut(other)
        gaps = [g for g in (self.gaps, o.gaps) if g is not None]
        return Cut(self.solid.union(o.solid), unary_union(gaps) if gaps else None)


def smooth(g, close=1.5, open_=1.0):
    """Blend the parts' joins (close the small notches), cut the deliberate gaps, then round the sharp corners."""
    c = g if isinstance(g, Cut) else Cut(g)
    g = c.solid.buffer(close, quad_segs=12).buffer(-close, quad_segs=12)
    if c.gaps is not None:
        g = g.difference(c.gaps)
    return g.buffer(-open_, quad_segs=12).buffer(open_, quad_segs=12)


def groove(body, pts, r, gap, root=1):
    """Lay a tail along pts over body, cut free of it by a gap past pts[root] so it reads as its own part; it stays
    joined to the body where it grows from (pts[:root + 1])."""
    tail = stroke(pts, r)
    return Cut(body | tail, stroke(pts[root:], r + gap).difference(tail))
