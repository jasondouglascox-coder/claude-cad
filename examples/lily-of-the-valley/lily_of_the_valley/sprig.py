"""The sprig in the wall's plane: the stem rising up the left and arching over, a pedicel off it to each bell
(out and up, over and down into the bell's apex), a small pointed bract at each pedicel's foot. Everything green
stays under the seam; the bells sit above it. All are shapes.sweep tubes, so none overhangs.
"""
import math
from functools import lru_cache

import numpy as np

from cadkit.mesh import Mesh
from lily_of_the_valley import bell, shapes
from lily_of_the_valley.params import Params

STEM_PTS = 90
PED_PTS = 40
BRACT_PTS = 20


@lru_cache
def stem_path(p: Params) -> np.ndarray:
    return shapes.bezier(p.stem, STEM_PTS)


def stem_radius(p: Params) -> np.ndarray:
    return np.linspace(*p.stem_r, STEM_PTS)


def stem(p: Params) -> Mesh:
    r = stem_radius(p)
    return shapes.sweep(stem_path(p), r, p.seam - r, label="stem")  # its top on the seam


def _on_stem(p: Params, k: int) -> tuple[int, np.ndarray, np.ndarray]:
    """Bell k's pedicel foot on the stem: (index, point, the stem's direction there)."""
    path = stem_path(p)
    i = round(p.bells[k][0] * (STEM_PTS - 1))
    tang = path[min(i + 1, STEM_PTS - 1)] - path[max(i - 1, 0)]
    return i, path[i], tang / np.linalg.norm(tang)


def frame(p: Params, k: int) -> tuple[np.ndarray, np.ndarray, float]:
    """Bell k's apex (plan), its axis (unit, apex to mouth: down, swung by its hang) and its size."""
    _, drop, out, size, hang = p.bells[k]
    _, foot, _ = _on_stem(p, k)
    a = math.radians(hang)
    return foot + np.array([out, -drop]), np.array([math.sin(a), -math.cos(a)]), size


def placed_bell(p: Params, k: int, recess: bool = True) -> Mesh:
    apex, axis, size = frame(p, k)
    return bell.local(p, size, recess).rotate_z(math.degrees(math.atan2(axis[1], axis[0]))).translate((*apex, 0))


def pedicel(p: Params, k: int) -> Mesh:
    """Out and up off the stem, over, and down into the apex along the bell's axis (2 mm in). It stays under the
    seam: where it meets the bell it runs in under the bell's shoulder, which hides it."""
    i, foot, tang = _on_stem(p, k)
    apex, axis, size = frame(p, k)
    out = p.bells[k][2]
    path = shapes.bezier([foot, foot + tang * 3 + np.array([abs(out) * 0.4 + 3, 7]), apex - axis * 9, apex + axis * 2],
                         PED_PTS)
    r = np.linspace(*p.pedicel_r, PED_PTS) * (0.85 + 0.15 * size)
    stem_z = p.seam - stem_radius(p)[i]
    z = np.minimum(np.full(PED_PTS, stem_z), p.seam - r - 0.2)
    return shapes.sweep(path, r, z, label="pedicel")


def bract(p: Params, k: int) -> Mesh:
    """A small pointed leaf at pedicel k's foot, lying along it, low and flat."""
    _, foot, tang = _on_stem(p, k)
    path = shapes.bezier([foot, foot + tang * 2 + np.array([3, 3]), foot + tang * 5 + np.array([5, 9])], BRACT_PTS)
    r = p.bract * np.sin(np.linspace(0.15, math.pi, BRACT_PTS)) ** 0.8 + 0.25
    return shapes.sweep(path, r, np.minimum(r * 0.5, p.seam - 0.5 - r * 0.45), flat=0.45, label="bract")


def parts(p: Params) -> list[Mesh]:
    n = len(p.bells)
    return ([stem(p)] + [pedicel(p, k) for k in range(n)] + [bract(p, k) for k in range(n)]
            + [placed_bell(p, k) for k in range(n)])
