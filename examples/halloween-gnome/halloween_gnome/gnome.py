"""The gnome as stacks of horizontal sections, meshed straight from the points: each body is rings of points round a
centre, one every p.dz up, capped flat. Nothing widens faster than p.flare per mm up, so nothing overhangs.

Assembly frame: the body stands on z = 0 round the z axis, face to -Y. The hat's own frame has its brim on z = 0;
the nose's has its flat back on z = 0 and points up."""
import math
from functools import lru_cache

import numpy as np

from cadkit.mesh import Mesh
from halloween_gnome.params import P, Params


def oriented(m: Mesh) -> Mesh:
    """Triangles turned to face out (positive volume)."""
    return m if m.volume >= 0 else Mesh(m.verts, m.tris[:, ::-1], m.label, m.color)


def stack(rings: list[np.ndarray], label: str = "", apex=None) -> Mesh:
    """A solid through rings of (n, 3) points, bottom first, each counter-clockwise seen from above, every ring
    star-shaped round its centre. Capped flat at the bottom, and at the top too unless it closes to an apex point
    (a roof with no flat at its top)."""
    n, k = len(rings[0]), len(rings)
    top = rings[-1].mean(0, keepdims=True) if apex is None else np.array([apex], float)
    verts = np.concatenate(rings + [rings[0].mean(0, keepdims=True), top])
    j = np.arange(n)
    tris = []
    for i in range(k - 1):
        a, b = i * n + j, i * n + (j + 1) % n
        c, d = b + n, a + n
        tris += [np.stack([a, b, c], 1), np.stack([a, c, d], 1)]
    lo, hi = k * n, k * n + 1
    tris += [np.stack([np.full(n, lo), (j + 1) % n, j], 1),
             np.stack([np.full(n, hi), (k - 1) * n + j, (k - 1) * n + (j + 1) % n], 1)]
    return oriented(Mesh(verts, np.concatenate(tris), label))


def levels(z0: float, z1: float, dz: float) -> np.ndarray:
    return np.linspace(z0, z1, max(2, round((z1 - z0) / dz) + 1))


def circle(r: float, z: float, n: int, centre=(0.0, 0.0)) -> np.ndarray:
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([centre[0] + r * np.cos(t), centre[1] + r * np.sin(t), np.full(n, z)], 1)


def prism(outline: np.ndarray, w0: float, w1: float, label: str = "") -> Mesh:
    """The convex outline (m, 2) in (u, v), counter-clockwise, from w0 to w1 along w: in its own (u, v, w) frame."""
    rings = [np.c_[outline, np.full(len(outline), w)] for w in (w0, w1)]
    return stack(rings, label)


def teardrop(r: float, angle: float, n: int = 49) -> np.ndarray:
    """(u, v) round a circle of radius r with a point toward -v, its flanks angle deg from the v axis: a peg or hole
    that prints lying down without support (or standing up, the same shape)."""
    a = math.radians(angle)
    tip = r / math.sin(a)  # where the flanks meet, below the centre
    t0 = -math.pi / 2 + (math.pi / 2 - a)  # where a flank leaves the circle (tangent)
    t = np.linspace(t0, t0 + 2 * math.pi - 2 * (math.pi / 2 - a), n)
    return np.r_[np.c_[r * np.cos(t), r * np.sin(t)], [[0.0, -tip]]]


def face_frame(m: Mesh) -> Mesh:
    """(u, v, w) = (x, z, out of the face): to the assembly frame, x stays, z = v, y = -w."""
    v = m.verts
    return oriented(Mesh(np.stack([v[:, 0], -v[:, 2], v[:, 1]], 1), m.tris, m.label, m.color))


# --- the body ---------------------------------------------------------------------------------------------------

def from_front(p: Params) -> np.ndarray:
    """Each ring point's angle from straight ahead (-Y), radians in -pi..pi."""
    t = np.linspace(0, 2 * math.pi, p.ring, endpoint=False)
    return (t + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi


def toes(p: Params) -> np.ndarray:
    """How far each ring point's boot toe sticks out at the bed, by angle."""
    phi = np.degrees(from_front(p))
    out = np.zeros(p.ring)
    for side in (-1, 1):
        d = (phi - side * p.toe_apart) / p.toe_w
        out = np.maximum(out, np.where(np.abs(d) < 1, np.cos(d * math.pi / 2) ** 2, 0.0))
    return p.toe * out


def nose_seat_r(p: Params) -> float:
    """The radius of the nose's flat back."""
    return math.sqrt(p.nose_r ** 2 - p.nose_back ** 2)


@lru_cache
def body_radii(p: Params) -> tuple[np.ndarray, np.ndarray]:
    """(zs, radii[z][point]) from the bed to the shoulder: boots, robe, beard and hair, each ring's radius by angle."""
    zs = levels(0, p.shoulder_h, p.dz)
    phi = from_front(p)
    t = np.linspace(0, 2 * math.pi, p.ring, endpoint=False)
    front = ((1 + np.cos(phi)) / 2) ** 2  # 1 straight ahead, 0 at the back
    toe = toes(p)
    rows = []
    for z in zs:
        if z <= p.boot_h + 1e-9:
            r = p.base_r + toe * math.sqrt(max(0.0, 1 - (z / p.boot_h) ** 2))
        elif z <= p.robe_h + 1e-9:
            r = np.full(p.ring, p.base_r + (p.robe_top_r - p.base_r) * (z - p.boot_h) / (p.robe_h - p.boot_h))
        else:
            s = min(1.0, max(0.0, (z - p.beard_z) / (p.nose_z - p.beard_z)))
            beard = p.face_r + (p.beard_r - p.face_r) * (1 + math.cos(math.pi * s)) / 2
            s = min(1.0, max(0.0, (z - p.beard_z) / (p.shoulder_h - p.beard_z)))
            hair = p.hair_top_r + (p.hair_r - p.hair_top_r) * (1 + math.cos(math.pi * s)) / 2
            r = hair + (beard - hair) * front
        rows.append(r)
    radii = np.array(rows)
    fade = 2.0  # mm: the strands grow in over this, up from the robe
    slack = p.strand / fade  # the most they widen a ring per mm up
    for i in range(1, len(zs)):  # never wider than the ring below allows, strands and all
        radii[i] = np.minimum(radii[i], radii[i - 1] + (p.flare - slack) * (zs[i] - zs[i - 1]))
    grow = np.clip((zs - p.robe_h) / fade, 0, 1)[:, None]
    return zs, radii + grow * p.strand * (1 + np.cos(p.strands * t)) / 2


def band(p: Params, z0: float, z1: float, label: str) -> Mesh:
    zs, radii = body_radii(p)
    t = np.linspace(0, 2 * math.pi, p.ring, endpoint=False)
    keep = (zs >= z0 - 1e-9) & (zs <= z1 + 1e-9)
    return stack([np.stack([r * np.cos(t), r * np.sin(t), np.full(p.ring, z)], 1)
                  for z, r in zip(zs[keep], radii[keep])], label)


@lru_cache
def face_depth(p: Params) -> float:
    """How far in front of the axis the nose's flat back sits: the least the face reaches forward anywhere behind
    the back (its disc, and up from it to the shoulder), so the back covers the flat cut there."""
    zs, radii = body_radii(p)
    phi = from_front(p)
    rb = nose_seat_r(p)
    near = np.abs(phi) < math.radians(70)
    depth = math.inf
    for z, r in zip(zs, radii):
        if z < p.nose_z - rb or z > p.shoulder_h:
            continue
        x, y = r[near] * np.sin(phi[near]), r[near] * np.cos(phi[near])  # y: forward
        half = rb if z >= p.nose_z else math.sqrt(max(0.0, rb ** 2 - (z - p.nose_z) ** 2))
        order = np.argsort(x)
        xs = np.linspace(-half, half, 21)
        depth = min(depth, float(np.interp(xs, x[order], y[order]).min()))
    return depth


def seat_cut(p: Params) -> Mesh:
    """Everything in front of the nose's flat back, under the ball's outline and up from it to the shoulder."""
    rb, n = p.nose_r, 49  # the ball's whole width: its sides bulge past the flat back
    t = np.linspace(math.pi, 2 * math.pi, n)
    d = np.r_[np.c_[rb * np.cos(t), p.nose_z + rb * np.sin(t)], [[rb, p.shoulder_h + 1], [-rb, p.shoulder_h + 1]]]
    return face_frame(prism(d, face_depth(p), p.beard_r + 5))


def peg(p: Params) -> Mesh:
    shape = teardrop(p.peg_r, p.peg_angle) + [0, p.nose_z]
    w = face_depth(p)
    return face_frame(prism(shape, w - 1.0, w + p.peg_len, "peg"))


def head(p: Params) -> Mesh:
    zs = levels(p.shoulder_h - 0.4, p.shoulder_h + p.head_h, p.dz)  # sunk into the shoulder: one solid
    tan = math.tan(math.radians(p.head_angle))
    return stack([circle(p.head_r - max(0.0, z - p.shoulder_h) * tan, z, p.ring) for z in zs], "head")


def tree_hole(p: Params) -> Mesh:
    r = p.hole_d / 2
    tan = math.tan(math.radians(p.hole_roof))
    apex = p.hole_depth + r / tan
    zs = np.r_[-0.5, levels(p.hole_depth, apex - p.dz, p.dz)]
    return stack([circle(r - max(0.0, z - p.hole_depth) * tan, z, p.ring) for z in zs], "hole", (0, 0, apex))


@lru_cache
def body(p: Params = P) -> list[Mesh]:
    """[black boots, orange robe, white beard + hair + head + peg], stacked by height, the tree hole up the middle."""
    hole = tree_hole(p)
    black = band(p, 0, p.boot_h, "body_black") - hole
    orange = band(p, p.boot_h, p.robe_h, "body_orange") - hole
    white = Mesh.union([band(p, p.robe_h, p.shoulder_h, "body_white"), head(p)]) - seat_cut(p) - hole
    white = Mesh.union([white, peg(p)])
    out = []
    for m, label, slot in ((black, "body_black", p.slot_black), (orange, "body_orange", p.slot_orange),
                           (white, "body_white", p.slot_white)):
        m = m.simplify()
        m.label, m.color = label, p.color(slot)
        out.append(m)
    return out


# --- the hat (its own frame: brim on the bed) ---------------------------------------------------------------------

def crown(p: Params, z: float) -> tuple[float, float]:
    """(centre's offset back (+Y), radius) of the crown's section at height z, above the band."""
    z0 = p.brim_t + p.band_h
    r = p.crown_r + (p.tip_r - p.crown_r) * (z - z0) / (p.hat_h - z0)
    return p.lean * max(0.0, z - p.lean_from) ** 2, r


def socket_r(p: Params, z: float) -> float:
    return p.head_r - z * math.tan(math.radians(p.head_angle))


def socket(p: Params) -> Mesh:
    apex = p.head_r / math.tan(math.radians(p.head_angle))
    return stack([circle(socket_r(p, z), z, p.ring) for z in np.r_[-0.5, levels(0, apex - p.dz, p.dz)]],
                 apex=(0, 0, apex))


@lru_cache
def hat(p: Params = P) -> list[Mesh]:
    """[black brim, orange band, black crown], the socket for the head up the middle."""
    z0, z1 = p.brim_t, p.brim_t + p.band_h
    hole = socket(p)
    brim = stack([circle(p.brim_r, z, p.ring) for z in (0, z0)]) - hole
    band_ = stack([circle(p.band_r, z, p.ring) for z in (z0, z1)]) - hole
    rings = []
    for z in levels(z1, p.hat_h, p.dz):
        c, r = crown(p, z)
        rings.append(circle(r, z, p.ring, (0.0, c)))
    top = stack(rings) - hole
    out = []
    for m, label, slot in ((brim, "hat_brim", p.slot_black), (band_, "hat_band", p.slot_orange),
                           (top, "hat_crown", p.slot_black)):
        m.label, m.color = label, p.color(slot)
        out.append(m)
    return out


# --- the nose (its own frame: flat back on the bed) ---------------------------------------------------------------

def nose_hole(p: Params) -> Mesh:
    """The peg's teardrop up to p.peg_len + p.peg_room, then a roof closing in on its round's centre no faster
    than p.flare per mm up: no flat ceiling to bridge."""
    shape = teardrop(p.peg_r + p.nose_fit / 2, p.peg_angle)
    depth = p.peg_len + p.peg_room
    far = np.hypot(shape[:, 0], shape[:, 1]).max()  # the teardrop's point, from the round's centre
    rise = far / p.flare
    rings = [np.c_[shape, np.full(len(shape), -0.5)]]
    for z in levels(depth, depth + rise - p.dz, p.dz):
        rings.append(np.c_[shape * (1 - (z - depth) / rise), np.full(len(shape), z)])
    return stack(rings, apex=(0, 0, depth + rise))


@lru_cache
def nose(p: Params = P) -> Mesh:
    top = p.nose_back + p.nose_r
    rings = [circle(math.sqrt(p.nose_r ** 2 - (z - p.nose_back) ** 2), z, p.ring)
             for z in levels(0, top - p.dz / 4, p.dz / 4)]
    hole = nose_hole(p)
    m = (stack(rings, apex=(0, 0, top)) - hole).simplify()
    m.label, m.color = "nose", p.color(p.slot_pink)
    return m


# --- assembled ----------------------------------------------------------------------------------------------------

def placed_nose(p: Params = P) -> Mesh:
    """The nose on its peg: its z out of the face (-Y), its y up."""
    v = nose(p).verts
    m = Mesh(np.stack([v[:, 0], -(face_depth(p) + v[:, 2]), p.nose_z + v[:, 1]], 1), nose(p).tris, "nose",
             nose(p).color)
    return oriented(m)


def placed_hat(p: Params = P) -> list[Mesh]:
    out = []
    for m in hat(p):
        h = m.translate((0, 0, p.shoulder_h))
        h.label, h.color = m.label, m.color
        out.append(h)
    return out


def assembled(p: Params = P) -> list[Mesh]:
    return body(p) + placed_hat(p) + [placed_nose(p)]
