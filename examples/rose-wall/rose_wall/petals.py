"""Rose petals. Each petal is its side profile swept round the flower's axis through the angle it wraps (an exact,
curved wall `wall` thick), trimmed to a lens: where two ellipsoids around its foot overlap, so it narrows to a
point at the tip. The side profile is a curve whose lean grows from upright at the foot to `lean` at the tip.
"""
import math
from functools import lru_cache

from build123d import Axis, Face, Part, Pos, Rot, Sphere, Wire, revolve, scale

from rose_wall.params import Params

GOLD = 137.508  # golden angle (deg): each petal turned this far from the last
STEPS = 28  # points along a petal's side


def lerp(pair: tuple, f: float) -> float:
    return pair[0] + (pair[1] - pair[0]) * f


def side(length: float, lean: float, bend: float, lip: float = 0.0) -> list[tuple[float, float, float]]:
    """(x out, z up, lean in radians) along a petal's side from its foot. The lean grows as t ** bend to `lean` deg
    at the tip; `lip` adds an outward roll (deg) over the last 15%."""
    pts, x, z = [(0.0, 0.0, 0.0)], 0.0, 0.0
    for k in range(1, STEPS + 1):
        t = k / STEPS
        a = math.radians(lean * t ** bend + lip * max(t - 0.85, 0) / 0.15)
        x += math.sin(a) * length / STEPS
        z += math.cos(a) * length / STEPS
        pts.append((x, z, a))
    return pts


def wall(p: Params, foot: float, line: list, half: float, point: float, back: bool = False) -> Part:
    """The petal along +X: its side `line` from a foot `foot` out, swept through +-half deg, trimmed to a lens.
    back: stretch the lens along X past the far side of the ring, so it shapes only the tip and the wrap stays whole."""
    inner = [(foot + x, z) for x, z, _ in line]
    outer = [(foot + x + p.wall * math.cos(a), z - p.wall * math.sin(a)) for x, z, a in line]
    outer[0] = (foot + p.wall, 0.0)
    prof = Face(Wire.make_polygon([(x, 0, max(z, 0)) for x, z in inner + outer[::-1]], close=True))
    swept = Rot(0, 0, -half) * revolve(prof, Axis.Z, 2 * half)
    tip = math.hypot(line[-1][0], line[-1][1])
    reach = foot + line[-1][0] + (p.wall if back else 0.0)
    width = reach * math.sin(math.radians(min(half, 85)))
    e = point * width
    along = max(tip, 2 * reach) if back else tip
    lens = None
    for sgn in (1, -1):
        ell = Pos(foot, sgn * e, 0) * scale(Sphere(1), (along * 1.01, width + e, tip * 1.01))
        lens = ell if lens is None else lens & ell
    return Part((swept & lens).solids())


def outer_f(p: Params, i: int) -> float:
    return i / (p.petals - 1)  # 0 innermost .. 1 outermost


def outer_foot(p: Params, i: int) -> float:
    return p.centre_r + (p.foot_r - p.centre_r) * outer_f(p, i) ** 0.9


def outer_wrap(p: Params, i: int) -> float:
    """Half the angle outer petal i wraps (deg)."""
    return lerp(p.wrap, outer_f(p, i))


@lru_cache
def outer(p: Params, i: int) -> Part:
    """Outer petal i (0 innermost), placed."""
    f = outer_f(p, i)
    line = side(lerp(p.length, f), p.lean[0] + (p.lean[1] - p.lean[0]) * f ** 0.7, p.bend)
    return Rot(0, 0, i * GOLD) * wall(p, outer_foot(p, i), line, outer_wrap(p, i), p.point)


def foot_reach(p: Params, angle: float) -> float:
    """How far out the petals' feet reach in this direction (deg): the outside of the outermost foot there."""
    covers = [i for i in range(p.petals) if abs((angle - i * GOLD + 180) % 360 - 180) <= outer_wrap(p, i)]
    return max(outer_foot(p, i) for i in covers) + p.wall


def pad(p: Params, i: int) -> Part:
    """The floor under outer petal i: a wedge from the centre out to the outside of its foot, as wide as it wraps.
    Together the pads tie every petal into one piece, and their edge is always a petal's foot: no lip."""
    prof = Face(Wire.make_polygon([(0, 0, 0), (outer_foot(p, i) + p.wall, 0, 0),
                                   (outer_foot(p, i) + p.wall, 0, p.floor), (0, 0, p.floor)], close=True))
    half = outer_wrap(p, i)
    return Rot(0, 0, i * GOLD - half) * revolve(prof, Axis.Z, 2 * half)


def centre_foot(p: Params, k: int) -> float:
    return p.centre_first + k * (p.wall + p.centre_gap)


def centre_line(p: Params, k: int) -> list[tuple[float, float, float]]:
    """Centre petal k's side, from its foot: shorter toward the middle (the funnel)."""
    g = k / max(p.centre_petals - 1, 1)
    return side(p.centre_top - p.centre_drop * (1 - g), lerp(p.centre_lean, g), 1.6, lip=p.centre_lip)


@lru_cache
def centre(p: Params, k: int) -> Part:
    """Centre petal k (0 innermost), placed: small, nearly upright, wrapped most of the way round, shorter toward the
    middle (the funnel)."""
    g = k / max(p.centre_petals - 1, 1)
    return Rot(0, 0, k * GOLD + p.centre_turn) * wall(p, centre_foot(p, k), centre_line(p, k),
                                                      lerp(p.centre_wrap, g), p.centre_point, back=p.centre_backs)
