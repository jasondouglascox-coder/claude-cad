"""A dozen cat poses as solid silhouettes, each built from blobs and strokes on the 100-unit grid (y up, ground at 0).

Only the outline is cut, so every pose has to read from its shape: ears, tail and legs carry it."""
from math import cos, sin

from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .params import P
from .shapes import circle, ellipse, face, groove, head, poly, smooth, stroke


def sitting():
    return unary_union([
        ellipse(40, 18, 20, 18),  # haunch
        ellipse(50, 38, 13, 22, -20),  # chest
        stroke([(58, 44), (60, 22), (61, 3)], 4.5, 3.8),  # front leg
        ellipse(63, 3, 5.5, 3),
        ellipse(52, 3, 8, 3),  # back foot
        head(60, 64, 1.3),
        stroke([(26, 6), (12, 4), (5, 9), (4, 20)], 4.5, 3.2),  # tail out behind, tip up
    ])


def from_behind():
    return unary_union([
        ellipse(50, 22, 21, 22),
        ellipse(50, 42, 15, 15),
        face(50, 65, 1.15),
        stroke([(60, 5), (74, 4), (82, 14), (81, 28), (75, 36), (70, 37)], 4.5, 3.2),
    ])


def lying():
    return unary_union([
        ellipse(45, 15, 30, 14),
        circle(24, 17, 15),
        stroke([(62, 5), (86, 4)], 4.5),  # front legs out
        ellipse(89, 4, 5.5, 3.6),
        head(74, 35, 1.3),
        stroke([(12, 5), (2, 3), (-9, 3.5), (-15, 9)], 4.2, 3.2),
    ])


def yarn():
    # the winding: two curved grooves cut through the ball, kept a min_feature in from its rim and from each other
    ball = circle(90, 15, 15).difference(unary_union([
        stroke([(75 + r * cos(t), 15 + r * sin(t)) for t in (-a, 0, a)], 2.6) for r, a in ((10, 0.4), (21, 0.2))
    ]))
    return unary_union([
        ellipse(38, 18, 20, 18),  # sitting, leaning in
        ellipse(48, 37, 13, 21, -30),
        stroke([(54, 40), (55, 22), (56, 3)], 4.5, 3.8),  # standing leg
        ellipse(58, 3, 5.5, 3),
        ellipse(48, 3, 8, 3),
        stroke([(56, 44), (68, 36), (78, 28)], 4.5, 4),  # paw out on the ball
        head(62, 58, 1.3, tilt=-20),
        ball,
        stroke([(102, 6), (109, 2.5), (117, 3), (123, 8)], 3.2),  # loose end
        stroke([(24, 6), (10, 4), (3, 9), (2, 20)], 4.5, 3.2),
    ])


def stretching():
    return unary_union([
        stroke([(26, 38), (45, 30), (62, 18)], 12, 9),
        stroke([(22, 32), (20, 15), (19, 2)], 6, 3.8),  # back legs
        stroke([(30, 30), (29, 15), (28, 2)], 5, 3.8),
        ellipse(22, 2.5, 6, 2.8),
        stroke([(60, 12), (78, 4), (92, 3)], 4.5, 3.8),  # front legs reaching
        ellipse(94, 3, 5.5, 3),
        head(74, 24, 1.25, tilt=8),
        stroke([(18, 42), (10, 54), (9, 67), (15, 74)], 4.5, 3.2),
    ])


def arched():
    return unary_union([
        stroke([(28, 32), (36, 48), (50, 54), (64, 48), (70, 34)], 9),  # the arch
        stroke([(28, 34), (27, 2)], 4.5, 3.8),
        stroke([(35, 38), (36, 2)], 4.5, 3.8),
        stroke([(64, 38), (64, 2)], 4.5, 3.8),
        stroke([(71, 36), (72, 2)], 4.5, 3.8),
        head(81, 38, 1.25, tilt=-15),
        stroke([(26, 40), (19, 58), (21, 78), (27, 85)], 6, 4.2),  # bristling tail straight up
    ])


def asleep():
    body = unary_union([
        ellipse(45, 26, 31, 18),
        head(72, 33, 1.3, tilt=-30),  # resting on its paws, ears up
    ])
    return groove(body, [(18, 18), (20, 8), (38, 4.5), (60, 4.5), (80, 7), (90, 14)], 4.5, 2.5, root=2)


def walking():
    return unary_union([
        ellipse(48, 37, 25, 11),
        circle(66, 37, 11),
        circle(30, 37, 12),
        stroke([(27, 32), (22, 17), (25, 2)], 5, 3.8),
        stroke([(34, 32), (39, 17), (37, 2)], 5, 3.8),
        stroke([(62, 32), (58, 16), (60, 2)], 4.5, 3.8),
        stroke([(69, 32), (72, 16), (73, 2)], 4.5, 3.8),
        head(83, 54, 1.25),
        stroke([(20, 41), (11, 53), (13, 69), (21, 75)], 4.2, 3.2),
    ])


def washing():
    body = unary_union([
        ellipse(40, 18, 20, 18),
        ellipse(48, 38, 12, 22, -12),
        stroke([(54, 42), (56, 22), (57, 3)], 4.5, 3.8),  # standing leg
        ellipse(59, 3, 5.5, 3),
        ellipse(49, 3, 8, 3),
        stroke([(26, 6), (12, 4), (5, 9), (4, 20)], 4.5, 3.2),
    ])
    body = groove(body, [(52, 46), (70, 42), (74, 56)], 4.5, 2.5, root=1)  # paw up, elbow out front
    return unary_union([body, ellipse(74, 58, 5, 4.5), head(56, 66, 1.3, tilt=-20)])


def pouncing():
    return unary_union([
        stroke([(28, 24), (50, 16), (66, 12)], 11, 9),
        circle(28, 22, 13),
        ellipse(32, 4.5, 11, 4.5),  # back feet gathered
        stroke([(62, 8), (78, 4)], 4.2),
        ellipse(80, 3.5, 6, 3.2),
        head(83, 20, 1.3, tilt=-5),
        stroke([(16, 26), (2, 30), (-12, 35)], 4.2, 3.2),  # tail out stiff
    ])


def reaching():
    return unary_union([
        ellipse(45, 40, 12, 22, -8),
        circle(42, 18, 14),
        ellipse(49, 3, 10, 3),
        head(43, 68, 1.2, tilt=28),
        stroke([(52, 50), (62, 66), (68, 82)], 4.5, 4),  # front paws up
        stroke([(50, 52), (58, 72), (60, 86)], 4.2, 3.8),
        stroke([(30, 8), (18, 4), (9, 9)], 4.2, 3.2),
    ])


def peeking():
    return unary_union([
        poly((0, 0), (100, 0), (100, 9), (0, 9)),  # the edge it peeks over
        face(50, 22, 1.25),
        ellipse(28, 10, 6.5, 4.5),
        ellipse(72, 10, 6.5, 4.5),
        stroke([(80, 1), (83, -14), (78, -26), (72, -28)], 4.2, 3.2),  # tail hanging down behind
    ])


POSES = {f.__name__: f for f in (sitting, from_behind, lying, yarn, stretching, arched, asleep, walking, washing,
                                 pouncing, reaching, peeking)}


def cat(name, p=P) -> Polygon:
    """The pose, smoothed, scaled so its longer side is cat_size (inches), its corner at the origin."""
    g = smooth(POSES[name]()).simplify(0.07)  # ~0.002": far finer than the blade follows
    if g.geom_type != "Polygon":
        raise ValueError(f"{name} came out in {len(g.geoms)} pieces")
    x0, y0, x1, y1 = g.bounds
    k = p.cat_size / max(x1 - x0, y1 - y0)
    return affinity.scale(affinity.translate(g, -x0, -y0), k, k, origin=(0, 0))
