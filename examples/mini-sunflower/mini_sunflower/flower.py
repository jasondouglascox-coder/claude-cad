"""The 3" sunflower, printed in one go, back on the bed: two rings of pointed yellow petals solid down to the bed,
a yellow riser under the head (hidden), a black disk on it, and the brown ring on that, rising round the eye (left
open, so the black shows sunk in the middle) and textured with diamonds where Vogel's two seed spirals cross.
Colours by height, two swaps. Meshes from point grids, unioned with manifold3d; it hangs on a nail through a keyhole
under the head.
"""
import math
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from build123d import Align, Cylinder, Pos, SlotCenterToCenter, extrude

from cadkit import bambu3mf, slicers
from cadkit.mesh import Mesh
from mini_sunflower.params import Params, Ring

NAIL_D = 3.0  # nail shank
MN = (Align.CENTER, Align.CENTER, Align.MIN)
ACROSS, ALONG = 41, 60  # petal grid: points across, sections along
ROUND = 720  # points round the head
RINGS = 90  # radii across the brown ring
GOLDEN = math.pi * (3 - math.sqrt(5))


def ease(points: tuple, x):
    """Through the (x, y) points, cosine-eased between them (level at each point), held flat past the ends."""
    xs, ys = np.array([q[0] for q in points]), np.array([q[1] for q in points])
    x = np.clip(np.asarray(x, float), xs[0], xs[-1])
    i = np.clip(np.searchsorted(xs, x, side="right") - 1, 0, len(xs) - 2)
    s = (x - xs[i]) / (xs[i + 1] - xs[i])
    return ys[i] + (ys[i + 1] - ys[i]) * (0.5 - 0.5 * np.cos(np.pi * s))


def smooth(a: float, b: float, x):
    s = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return s * s * (3 - 2 * s)


# petals

def half_width(p: Params, rg: Ring, t):
    a, b = p.petal_shape
    return np.maximum(rg.width / 2 * np.sin(np.pi * np.clip(t, 0, 1) ** a) ** b, 0.05)


def petal(p: Params, rg: Ring) -> Mesh:
    """One petal along +X, solid down to the bed: high along the midrib, its top falling to one layer at the
    edges and the tip (it angles all the way to the wall), with vein grooves."""
    t = np.linspace(0, 1, ALONG)
    v = np.linspace(-1, 1, ACROSS)
    V, T = np.meshgrid(v, t, indexing="ij")
    X = np.broadcast_to(rg.r0 + (rg.r1 - rg.r0) * t, V.shape)
    Y = V * half_width(p, rg, t)[None, :]
    mid, edge = ease(rg.mid, T), ease(rg.edge, T)
    Z = edge + (mid - edge) * (1 - V ** 2)
    for k in range(1, p.veins + 1):
        Z = Z - p.vein_depth * np.exp(-((V - (-1 + 2 * k / (p.veins + 1))) / 0.12) ** 2) * np.sin(np.pi * T)
    top = np.stack([X, Y, np.maximum(Z, p.printer.layer)], -1)
    return Mesh.from_grids(top, np.stack([X, Y, np.zeros_like(Z)], -1), "petal")


def sized(rg: Ring, p: Params, k: int) -> Ring:
    """Petal k of a ring, a little shorter and narrower than the ring's own by the golden angle's walk (petal 0
    full size): no two alike, as on a real flower, and no two neighbours mirror images (their edges would meet
    edge to edge)."""
    s = 0.5 - 0.5 * math.cos(k * GOLDEN)
    return replace(rg, r1=rg.r0 + (rg.r1 - rg.r0) * (1 - p.vary[0] * s), width=rg.width * (1 - p.vary[1] * s))


def angles(p: Params) -> list[tuple[Ring, float]]:
    """(petal's ring, angle in degrees) of every petal: the front ring over the back ring's gaps."""
    pitch = 360 / p.petals
    return ([(sized(p.back, p, k), k * pitch) for k in range(p.petals)]
            + [(sized(p.front, p, k + p.petals), (k + 0.5) * pitch) for k in range(p.petals)])


def reach(p: Params, deg: float) -> float:
    """How far out from the centre the petals reach at this angle (the flower's outline)."""
    best = 0.0
    for rg, a in angles(p):
        d = abs((deg - a + 180) % 360 - 180)
        t = np.linspace(0, 1, 4001)
        r, hw = rg.r0 + (rg.r1 - rg.r0) * t, half_width(p, rg, t)
        inside = np.degrees(np.arctan2(hw, r)) >= d
        if inside.any():
            best = max(best, float(np.hypot(r, hw)[inside].max()) if d < 1e-9 else float(r[inside].max()))
    return best


# the head

def ring_grid(r: np.ndarray, th: np.ndarray, z: np.ndarray, z0: float, label: str) -> Mesh:
    """A closed solid over an annulus (r[0] > 0): the top skin z[i, j] at radius r[i], angle th[j] (all the way
    round, not repeating th[0]); a flat bottom at z0; a wall straight down inside. Outside the top comes down to
    z0 itself (z[-1] == z0): a sharp edge, no wall."""
    nr, nt = len(r), len(th)
    R, TH = np.meshgrid(r, th, indexing="ij")
    top = np.stack([R * np.cos(TH), R * np.sin(TH), z], -1).reshape(-1, 3)
    bot = np.stack([r[0] * np.cos(th), r[0] * np.sin(th), np.full(nt, z0)], -1)
    assert np.allclose(z[-1], z0)
    t = np.arange(nr * nt).reshape(nr, nt)
    b = np.stack([nr * nt + np.arange(nt), t[-1]])  # the bottom's inner ring, and its outer ring: the top's edge
    nxt = np.roll(np.arange(nt), -1)
    quads = [(t[:-1, :], t[1:, :], t[1:, nxt], t[:-1, nxt]),  # top, facing up
             (b[0], b[0, nxt], b[1, nxt], b[1]),  # bottom
             (t[0], t[0, nxt], b[0, nxt], b[0])]  # inner wall
    tris = []
    for a, bb, c, d in quads:
        tris += [np.stack([a, bb, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)]
    m = Mesh(np.concatenate([top, bot]), np.concatenate(tris), label)
    return m if m._manifold().volume() > 0 else Mesh(m.verts, m.tris[:, ::-1], label)


def round_angles() -> np.ndarray:
    """The head's points round: half a step off the petals' axes (whole degrees), so no petal's midrib or edge
    lands on one of them (the union would leave edges touching edge to edge)."""
    return (np.arange(ROUND) + 0.5) * 2 * np.pi / ROUND


def disk(r0: float, r1: float, z0: float, z1: float, label: str) -> Mesh:
    """A flat-topped disk, r0 across its bottom at z0 and r1 across its top at z1, with the head's points round
    its edges (so the colours line up)."""
    th = round_angles()
    ring = lambda r, z: np.c_[r * np.cos(th), r * np.sin(th), np.full(ROUND, z)]
    verts = np.concatenate([ring(r0, z0), ring(r1, z1), [[0, 0, z0], [0, 0, z1]]])
    j, k = np.arange(ROUND), np.roll(np.arange(ROUND), -1)
    lo, hi = 2 * ROUND, 2 * ROUND + 1
    tris = np.concatenate([np.stack([np.full(ROUND, lo), k, j], -1), np.stack([np.full(ROUND, hi), ROUND + j, ROUND + k], -1),
                           np.stack([j, k, ROUND + k], -1), np.stack([j, ROUND + k, ROUND + j], -1)])
    return Mesh(verts, tris, label)


def run(p: Params, h: float) -> float:
    """How far in the head's side goes rising h: it angles up at p.side from level."""
    return h / math.tan(math.radians(p.side))


def rim_r(p: Params) -> float:
    """Where the brown starts: the black's top edge, in from the head's edge by its angled side."""
    return p.head_r - run(p, p.black_t)


def brown_top(p: Params, r, th):
    """The brown ring's top at (r, theta): its eased profile on the black, angling up from nothing at the black's
    edge (a soft minimum of the profile and a p.side slope from rim_r), plus the spiral diamonds. Each spiral
    family F is cos(F theta - d_F r^2 / c^2) with d_F the golden angle's drift over F seeds: 1 on every seed, so
    two families' product peaks in a diamond on each seed."""
    r, th = np.asarray(r, float), np.asarray(th, float)
    f = 1.0
    for F in p.spirals:
        d = F * GOLDEN - 2 * math.pi * round(F * GOLDEN / (2 * math.pi))
        f = f * (0.5 + 0.5 * np.cos(F * th - d * r ** 2 / p.seed_c ** 2))
    rim = rim_r(p)
    fade = smooth(p.eye_r, p.eye_r + p.texture_edge, r) * smooth(rim, rim - p.texture_edge, r)
    cone = np.maximum(rim - r, 0) * math.tan(math.radians(p.side))
    k = 0.15  # the soft minimum's rounding (mm)
    lo = np.minimum(ease(p.brown, r), cone)
    h = lo - k * np.log(np.exp(-(ease(p.brown, r) - lo) / k) + np.exp(-(cone - lo) / k))
    h = np.where(r >= rim, 0.0, np.clip(h, 0, None))
    return p.brown_z + h + p.texture * f ** 0.6 * fade


def brown(p: Params) -> Mesh:
    r = np.linspace(p.eye_r, rim_r(p), RINGS)
    th = round_angles()
    R, TH = np.meshgrid(r, th, indexing="ij")
    return ring_grid(r, th, brown_top(p, R, TH), p.brown_z, "flower_brown")


# hanging

def key_top(p: Params) -> float:
    """The keyhole's flat roof: the one face that looks down (a short bridge)."""
    return p.key_lip + p.key_head_room


def keyhole(p: Params) -> list:
    """Cut from below, the slot running down from the nail: the shank's slot through a lip, the entry hole below
    it, the head's room above the lip, flat-roofed."""
    end = p.hang_y + NAIL_D / 2 - p.key_shank_w / 2  # the slot's top arc centre: the nail rests against it
    at = Pos(0, end - p.key_len / 2, 0)
    slot = lambda w: SlotCenterToCenter(p.key_len, w, rotation=90)
    return [at * Pos(0, 0, -1) * extrude(slot(p.key_shank_w), p.key_lip + 1),
            Pos(0, end - p.key_len, -1) * Cylinder(p.key_head_d / 2, p.key_lip + 1, align=MN),
            at * Pos(0, 0, p.key_lip) * extrude(slot(p.key_head_d), p.key_head_room)]


# the flower

@lru_cache
def parts(p: Params) -> tuple[Mesh, Mesh, Mesh]:
    """(yellow, black, brown), unkeyed."""
    yellow = Mesh.union([petal(p, rg).rotate_z(a) for rg, a in angles(p)] + [disk(p.head_r + run(p, p.black_z), p.head_r, 0, p.black_z, "riser")])
    return yellow, disk(p.head_r, rim_r(p), p.black_z, p.brown_z, "flower_black"), brown(p)


@lru_cache
def unkeyed(p: Params) -> Mesh:
    return Mesh.union(list(parts(p)), "flower")


@lru_cache
def coloured(p: Params) -> list[tuple[Mesh, int]]:
    """[(yellow, slot), (black, slot), (brown, slot)], the keyhole cut from the yellow."""
    yellow, black, brn = parts(p)
    for c in keyhole(p):
        yellow = yellow - c
    out = []
    for m, label, slot in ((yellow, "flower_yellow", p.slot_yellow), (black, "flower_black", p.slot_black),
                           (brn, "flower_brown", p.slot_brown)):
        m = m.drop_crumbs(1.0).simplify()
        m.label, m.color = label, p.color(slot)
        out.append((m, slot))
    return out


@lru_cache
def body(p: Params) -> Mesh:
    return Mesh.union([m for m, _ in coloured(p)], "flower")


# the plate

def centre_xy(p: Params) -> tuple[float, float]:
    return p.printer.bed / 2, (p.printer.bed_y or p.printer.bed) / 2


def spots(p: Params) -> list[tuple[float, float]]:
    """Each flower's centre on the bed: per_plate of them in a square pitch apart, round the bed's middle."""
    cx, cy = centre_xy(p)
    if p.per_plate == 1:
        return [(cx, cy)]
    assert p.per_plate == 4, "one flower a plate, or four"
    d = p.pitch / 2
    return [(cx - d, cy - d), (cx + d, cy - d), (cx - d, cy + d), (cx + d, cy + d)]


def tower(p: Params) -> tuple[float, float, float]:
    """Prime tower (x, y, width): in the middle of the four (or the front-left corner, for one)."""
    if p.per_plate == 1:
        return (4.0, 4.0, p.tower_w)
    cx, cy = centre_xy(p)
    return (cx - p.tower_w / 2, cy - p.tower_w / 2, p.tower_w)


def plate(p: Params) -> list[tuple[str, list[tuple[str, Mesh, int]]]]:
    return [(f"mini_sunflower_{k + 1}", [(m.label, m.translate((x, y, 0)), slot) for m, slot in coloured(p)])
            for k, (x, y) in enumerate(spots(p))]


def write(p: Params, out: Path) -> Path:
    """out/plates/mini_sunflowers.3mf: an object per flower, its yellow, black and brown bodies as parts; the STL;
    plates.csv. Returns the slicer settings it wrote (where the prime tower is)."""
    out = Path(out)
    (out / "plates").mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments), tower=tower(p))
    objects = plate(p)
    s = slicers.active()
    s.write_project(out / "plates" / f"mini_sunflowers{s.project_suffix}", objects, settings)
    Mesh.union([m for _, ps in objects for _, m, _ in ps]).write_stl(out / "plates" / "mini_sunflowers.stl")
    (out / "plates.csv").write_text(f"plate,quantity,contents\nmini_sunflowers,1,"
                                    f"sunflower x{len(objects)} ({p.color_changes} colour changes)\n")
    return settings
