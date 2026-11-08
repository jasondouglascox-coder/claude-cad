"""A dozen cat poses as solid silhouettes, each built from blobs and strokes on the 100-unit grid (y up, ground at 0).

Only the outline is cut, so every pose has to read from its shape: ears, tail and legs carry it."""
from shapely import affinity
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union

from .params import P
from .shapes import (blend, butterfly, circle, ellipse, face, ground, groove, head, hull, outline, pieces, poly, profile,
                     smooth, stroke, yarn_ball, Cut, fur)


def sitting():
    # one outline up the back from the nape, round the haunch, along the ground, up the front leg and chest to the
    # throat; the head sits over its top
    body = outline([(57, 75), (49, 65), (40, 55), (30, 43), (22, 31), (19, 19), (21, 8), (28, 1.5), (38, 0), (52, 0),
                    (62, 0), (70, 0.2), (72, 2.5, "sharp"), (68, 5), (66.5, 15), (66.5, 30), (68.5, 44), (70, 56),
                    (68.5, 66), (64, 72)])
    return unary_union([
        ground(body),
        profile(63, 78, 1.3),
        stroke([(26, 5), (14, 2.5), (5, 5), (0, 12), (1, 21)], 3.8, 3),  # tail out behind, tip up
    ])


def from_behind():
    # the head as big as the reference draws it, a soft neck, the body a pear down to a flat seat, a hind foot
    # peeking out on the right
    body = outline([(50, 62), (58, 59), (62, 55), (67, 47), (72, 37), (75, 26), (75, 15), (77, 7), (80, 3), (78, 0),
                    (60, 0), (40, 0), (28, 1), (24, 8), (24, 20), (27, 32), (32, 44), (37, 53), (42, 59)])
    return unary_union([
        ground(body),
        face(50, 72, 1.15),
        stroke([(33, 3), (22, 4), (15, 12), (13, 26), (15, 39), (20, 47)], 3.2, 3.9),  # tail up the side, tip fuller
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
    return yarn_ball(92, 17, 17, strand=[(104, 6), (109, 2.5), (117, 3), (123, 8)]) | unary_union([
        ellipse(38, 18, 20, 18),  # sitting, leaning in
        ellipse(48, 37, 13, 21, -30),
        stroke([(54, 40), (55, 22), (56, 3)], 4.5, 3.8),  # standing leg
        ellipse(58, 3, 5.5, 3),
        ellipse(48, 3, 8, 3),
        stroke([(56, 44), (68, 36), (78, 28)], 4.5, 4),  # paw out on the ball
        head(62, 58, 1.3, tilt=-20),
        stroke([(24, 6), (10, 4), (3, 9), (2, 20)], 4.5, 3.2),
    ])


def stretching():
    # a play-bow facing left: front legs flat out along the ground, chest low, rump high on a straight hind leg, the
    # tail arching up and over
    body = outline([(0.5, 3), (6, 6), (20, 10), (30, 15), (34, 22), (48, 26), (53, 25), (60, 32), (70, 43),
                    (80, 51), (90, 56), (98, 50), (100, 38), (97, 22), (95, 10), (94.5, 3), (93, 0), (82, 0),
                    (83.5, 3), (88, 12), (87, 24), (82, 26), (70, 20), (55, 13), (40, 8), (25, 3.5), (8, 0.5), (2, 0.8)])
    return unary_union([
        ground(body),
        profile(33, 27, 1.25, tilt=8, facing=-1),
        stroke([(89, 54), (95, 70), (93, 88), (84, 99), (70, 103), (60, 100)], 4.5, 3.5),
    ])


def arched():
    # the Halloween cat, facing you: back bristling up in an arch on straight legs, tail puffed up
    back = [(30, 30), (38, 46), (52, 54), (66, 50), (74, 36)]
    tail = [(74, 40), (84, 54), (93, 70), (101, 86), (106, 98)]  # up and back
    return unary_union([
        stroke(back, 10),
        fur(back, 9.5, 10, 10),
        stroke([(30, 32), (28, 16), (27, 2)], 5.5, 3.2),  # front legs
        ellipse(26, 2.6, 4.5, 2.6),
        stroke([(36, 36), (36, 16), (37, 2)], 5, 3.2),
        ellipse(36, 2.6, 4.5, 2.6),
        stroke([(68, 38), (68, 18), (67, 2)], 6, 3.2),  # hind legs
        ellipse(66, 2.6, 4.5, 2.6),
        stroke([(74, 36), (77, 17), (78, 2)], 6, 3.2),
        ellipse(79, 2.6, 4.5, 2.6),
        stroke(tail, 8, 4),  # puffed
        fur(tail, 7, 9, 10, 1),
        fur(tail, 7, 9, 10, -1),
        face(21, 40, 1.3),
    ])


def asleep():
    # long and low facing left, head down on its front paws, ears up; notches from the ground mark the paw under the
    # chin and the curled hind leg
    body = outline([(3.3, 0), (2.9, 3.3), (4.4, 8.8), (3.5, 12), (-1.5, 24, "sharp"), (9, 19.5), (14, 21.5),
                    (20, 27), (23.5, 37, "sharp"), (28, 26.5, "sharp"), (36, 29), (46, 31), (64.9, 28), (84.7, 21),
                    (95.7, 13.2), (100, 5.5), (99, 0), (50, 0)])
    paw = stroke([(14, -1), (14.5, 5), (19, 7)], 1.8)
    leg = stroke([(66, -1), (65, 6), (70, 11), (82, 12), (92, 9)], 1.8)
    return Cut(ground(body), unary_union([paw, leg]))


def walking():
    return unary_union([
        hull(ellipse(68, 42, 13, 12), ellipse(31, 43, 15, 12)),
        hull(circle(70, 47, 9), circle(82, 58, 6)),  # neck
        profile(86, 60),
        stroke([(28, 42), (22, 26), (15, 12), (12, 3)], 9, 2.8),  # hind, stepping back: thigh to hock to paw
        ellipse(14, 2.6, 4.6, 2.6),
        stroke([(36, 40), (40, 25), (35, 12), (37, 3)], 8, 2.8),  # hind, forward
        ellipse(39, 2.6, 4.6, 2.6),
        stroke([(64, 38), (61, 20), (59, 3)], 6.5, 2.8),  # front, back
        ellipse(61, 2.6, 4.6, 2.6),
        stroke([(71, 38), (77, 20), (82, 3)], 6.5, 2.8),  # front, reaching forward
        ellipse(84, 2.6, 4.6, 2.6),
        stroke([(19, 48), (13, 58), (11, 72), (15, 84), (21, 88)], 3.6, 2.6),  # tail up, tip curling forward
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
    return body | unary_union([ellipse(74, 58, 5, 4.5), head(56, 66, 1.3, tilt=-20)])


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


def butterflies():
    # sitting up on its haunch, head tipped back, both paws up after three butterflies (each its own cut)
    body = outline([(31, 0), (21, 5), (16, 17), (18, 31), (24, 44), (31, 56), (38, 66), (46, 70), (52, 62), (55, 50),
                    (56, 36), (58, 22), (61, 11), (66, 4), (66, 0)])
    cat = unary_union([
        ground(body),
        profile(46, 75, 1.2, tilt=30),
        stroke([(50, 60), (59, 72), (66, 86)], 5, 3.2),  # one paw high
        circle(67, 88, 3.8),
        stroke([(52, 55), (65, 62), (77, 67)], 5, 3.2),  # one reaching out
        circle(79, 68, 3.8),
        stroke([(24, 4), (12, 3), (4, 10), (2, 22), (6, 32), (13, 34), (15, 28)], 3.6, 3.2),  # tail curled on the ground
    ])
    return cat, butterfly(84, 106, 1.05, 15), butterfly(113, 90, 1.0, -12), butterfly(104, 61, 0.95, 20)


def peeking():
    return unary_union([
        poly((0, 0), (100, 0), (100, 9), (0, 9)),  # the edge it peeks over
        face(50, 22, 1.25),
        ellipse(28, 10, 6.5, 4.5),
        ellipse(72, 10, 6.5, 4.5),
        stroke([(80, 1), (83, -14), (78, -26), (72, -28)], 4.2, 3.2),  # tail hanging down behind
    ])


POSES = {f.__name__: f for f in (sitting, from_behind, lying, yarn, stretching, arched, asleep, walking, washing,
                                 pouncing, butterflies, peeking)}


def parts(name):
    """The pose's separate cuts: the cat, then any extras (a yarn ball)."""
    g = POSES[name]()
    return g if isinstance(g, tuple) else (g,)


def part_count(name):
    return len(parts(name))


def cat(name, p=P):
    """The pose, each part smoothed on its own, scaled so the longer side is cat_size (inches), corner at the origin:
    a Polygon, or a MultiPolygon when the pose has extras."""
    out = []
    for g in parts(name):
        g = smooth(g).simplify(0.07)  # ~0.002": far finer than the blade follows
        if g.geom_type != "Polygon":
            raise ValueError(f"{name}: a part came out in {len(g.geoms)} pieces")
        out.append(g)
    g = out[0] if len(out) == 1 else MultiPolygon(out)
    x0, y0, x1, y1 = g.bounds
    k = p.cat_size / max(x1 - x0, y1 - y0)
    return affinity.scale(affinity.translate(g, -x0, -y0), k, k, origin=(0, 0))
