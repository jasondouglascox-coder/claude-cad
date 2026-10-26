"""A bell, lying in the wall's plane along +X from its apex (where the pedicel joins) at the origin, its axis at
bell_z. Its sections are shapes.section: round above, the 45-degree fill under. Along the axis: a rounded
shoulder, straight-ish sides widening a little, a slight waist and a flared rim, scalloped into six lobes whose
points reach past it. The two lobes at the sides curl back in the wall's plane (they lie at the bell's widest, so
they print like the rest); a wide shallow cone hollows the mouth.
"""
import math
from functools import lru_cache

import numpy as np

from cadkit.mesh import Mesh
from lily_of_the_valley import shapes
from lily_of_the_valley.params import Params

ROWS = 44  # sections along the axis
INNER = 0.4  # the mouth's cap: lobe points to a ring this fraction of the rim's size
SHOULDER, WAIST, FLARE = 0.36, 0.84, 0.86  # where along the bell (0 apex .. 1 rim) each starts or sits


def profile(t, p: Params | None = None) -> np.ndarray:
    """Radius / bell radius along the axis, apex (t = 0) to rim (t = 1)."""
    flare = p.flare if p else Params.flare
    sh = np.sin(np.pi / 2 * np.clip(t / SHOULDER, 0, 1)) ** 0.55
    r = 0.18 + 0.74 * sh + 0.10 * np.clip((t - SHOULDER) / (FLARE - 0.06 - SHOULDER), 0, 1)
    r = r - 0.05 * np.exp(-((t - WAIST) / 0.07) ** 2)
    return r + flare * np.clip((t - FLARE) / (1 - FLARE), 0, 1) ** 2


def rim(p: Params, size: float) -> float:
    """The rim's widest (at a lobe point)."""
    return p.bell_r * size * profile(1.0, p) * (1 + p.lobe)


def _body(p: Params, size: float) -> Mesh:
    R = p.bell_r * size
    L = p.bell_len * R
    rings = []
    for t in np.linspace(0, 1, ROWS):
        f = np.clip((t - 0.78) / 0.22, 0, 1) ** 2  # the scallops grow in toward the rim
        lobe = lambda th: (1 + f * p.lobe * np.cos(p.lobes * th)) / (1 + f * p.lobe)
        w, z, th = shapes.section(R * profile(t, p) * (1 + f * p.lobe), p.bell_z, p.bell_flat, lobe)
        a = np.nan_to_num(th, nan=-1.0)
        point = np.clip(np.cos(p.lobes * a), 0, 1) * (a > math.pi / 6) * (a < 5 * math.pi / 6)  # front lobes only
        rings.append(np.stack([t * L + f * p.lobe_push * R * point, w, z], 1))
    # the mouth: in from the lobe points to a ring at the rim's plane, then a fan (the recess cuts most of it away);
    # a fan straight from the points would lean out over air
    inner = rings[-1].copy()
    inner[:, 0] = L
    inner[:, 1:] = INNER * inner[:, 1:] + (1 - INNER) * np.array([0.0, p.bell_z])
    rings.append(inner)
    return shapes.tube(rings, "bell")


def _recess(p: Params, size: float) -> Mesh:
    """A cone into the mouth along the axis, its roof shallower than 45, narrow enough at the mouth that it runs out
    under the lobe points without cutting them off."""
    R = p.bell_r * size
    L, depth, rm = p.bell_len * R, p.recess * R, 0.45 * rim(p, size)
    th = np.linspace(0, 2 * math.pi, 48, endpoint=False)
    rings = [np.stack([np.full_like(th, x), r * np.cos(th), p.bell_z + p.bell_flat * r * np.sin(th)], 1)
             for x, r in ((L - depth, 0.3), (L + 4, rm + 4 * rm / depth))]
    return shapes.tube(rings)


def _horns(p: Params, size: float) -> list[Mesh]:
    """The side lobes, curling out and back toward the apex, lying at the bell's widest."""
    R, rr = p.bell_r * size, rim(p, size)
    L = p.bell_len * R
    out = []
    for s in (1, -1):
        path = shapes.bezier([(L - 3.0, s * (rr - 2.5)), (L + 1.8, s * (rr - 0.5)), (L + 0.8, s * (rr + 2.2)),
                              (L - 1.4, s * (rr + 2.6))], 24)
        out.append(shapes.sweep(path, np.linspace(*p.horn, 24) * (0.6 + 0.4 * size), p.bell_z, 0.7))
    return out


@lru_cache
def local(p: Params, size: float, recess: bool = True) -> Mesh:
    """The whole bell, apex at the origin, mouth toward +X."""
    m = Mesh.union([_body(p, size)] + _horns(p, size), "bell")
    return m - _recess(p, size) if recess else m
