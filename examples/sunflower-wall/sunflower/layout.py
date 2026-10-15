"""Pure math (no CAD): petal angles, quarter boundaries, pin and seed positions, petal shape functions."""
import math

from sunflower.params import Params, Ring

GOLDEN = math.pi * (3 - math.sqrt(5))


def validate(p: Params) -> None:
    if p.petals % 4 or p.petals < 8:
        raise ValueError(f"petals = {p.petals}: need a multiple of 4, at least 8, so the quarters are identical")


def back_angles(p: Params) -> list[float]:
    return [k * p.pitch for k in range(p.petals)]


def front_angles(p: Params) -> list[float]:
    """Front petals sit over the back ring's gaps."""
    return [(k + 0.5) * p.pitch for k in range(p.petals)]


def back_start(p: Params) -> float:
    """First back quarter boundary: a back-petal gap (a front petal covers it)."""
    return p.pitch / 2


def front_start(p: Params) -> float:
    """First front quarter boundary: the front-petal gap nearest 45 degrees past the back one (brick bond)."""
    return round((back_start(p) + 45) / p.pitch) * p.pitch


def boundaries(p: Params, layer: str) -> list[float]:
    a0 = back_start(p) if layer == "back" else front_start(p)
    return [a0 + 90 * q for q in range(4)]


def pin_angles(p: Params) -> list[float]:
    """Midway between each pair of neighbouring back/front boundaries: each pin ties one quarter of each ring."""
    b = sorted(a % 360 for a in boundaries(p, "back") + boundaries(p, "front"))
    return [(x + ((y - x) % 360) / 2) % 360 for x, y in zip(b, b[1:] + b[:1])]


def in_quarter(angle: float, start: float) -> bool:
    return 0 < (angle - start) % 360 < 90


def half_width(ring: Ring, r: float) -> float:
    """Petal half width at radius r: zero at both ends, widest a little past the middle, pointed tip."""
    s = (r - ring.r0) / (ring.r1 - ring.r0)
    if s <= 0 or s >= 1:
        return 0.0
    return ring.width / 2 * math.sin(math.pi * s) ** 0.6


def midrib(ring: Ring, r: float) -> float:
    """Top of the petal along its midrib: smoothstep through the profile points."""
    pts = ring.profile
    if r <= pts[0][0]:
        return pts[0][1]
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if r <= r1:
            t = (r - r0) / (r1 - r0)
            return z0 + (z1 - z0) * t * t * (3 - 2 * t)
    return pts[-1][1]


def seeds(p: Params) -> list[tuple[float, float, float, float]]:
    """(x, y, diameter, height) per seed, Vogel's spiral; heights on layer multiples."""
    out = []
    lim = p.center_r - p.seed_edge
    i = 0
    while True:
        i += 1
        r = p.seed_c * math.sqrt(i)
        if r > lim:
            return out
        d = next(d for rr, d in p.seed_zones if r < rr)
        h0, h1 = p.seed_h
        h = round((h0 + (h1 - h0) * (r / lim) ** 2) / p.printer.layer) * p.printer.layer
        out.append((r * math.cos(i * GOLDEN), r * math.sin(i * GOLDEN), d, h))


def pin_y(p: Params) -> dict:
    """Pin profile stations along its length (y = 0 at the head's underside = the wall)."""
    barb = p.back_t + p.front_t + p.throat + p.fit / 2
    return {"head": p.pin_head, "barb": barb, "tip": barb + p.pin_tip}
