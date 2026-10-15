"""Shaded PNG previews: flat-shaded, z-buffered, in each part's color. Look at the result before calling a visible
change right; hidden-line SVGs (cadkit.export.write_svg) don't show colors or depth.

Needs the `render` extra (numba, pillow).
"""
from pathlib import Path

import numpy as np
from build123d import Color, Shape
from numba import njit
from PIL import Image

TOP = (0, 0, 1)  # view direction toward the eye
ISO = (0.0, -1.0, 0.6)
LIGHT = (-0.45, 0.55, 1.0)


@njit(cache=True)
def _raster(px, py, pz, col, size, zbuf, img):
    for t in range(px.shape[0]):
        x0, x1, x2 = px[t, 0], px[t, 1], px[t, 2]
        y0, y1, y2 = py[t, 0], py[t, 1], py[t, 2]
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(d) < 1e-12:
            continue
        lo_x, hi_x = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, size - 1)
        lo_y, hi_y = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, size - 1)
        for y in range(lo_y, hi_y + 1):
            for x in range(lo_x, hi_x + 1):
                a = ((y1 - y2) * (x + 0.5 - x2) + (x2 - x1) * (y + 0.5 - y2)) / d
                b = ((y2 - y0) * (x + 0.5 - x2) + (x0 - x2) * (y + 0.5 - y2)) / d
                c = 1.0 - a - b
                if a < -1e-6 or b < -1e-6 or c < -1e-6:
                    continue
                z = a * pz[t, 0] + b * pz[t, 1] + c * pz[t, 2]
                if z > zbuf[y, x]:
                    zbuf[y, x] = z
                    img[y, x, 0], img[y, x, 1], img[y, x, 2] = col[t, 0], col[t, 1], col[t, 2]


def _rgb(color) -> np.ndarray:
    return np.array(tuple(color)[:3] if isinstance(color, Color) else color, float)


def render(items: list[tuple[Shape, Color]], path: Path, view: tuple = ISO, px: int = 1000, tol: float = 0.1,
           bg: tuple = (201, 183, 156)) -> None:
    """Orthographic view of (shape, color) items looking along -view, z-up (or y-up when looking straight down)."""
    v = np.array(view, float)
    v /= np.linalg.norm(v)
    up = np.array([0, 0, 1.0]) if abs(v[2]) < 0.9 else np.array([0, 1.0, 0])
    xr = np.cross(up, v)
    xr /= np.linalg.norm(xr)
    yr = np.cross(v, xr)
    light = np.array(LIGHT) / np.linalg.norm(LIGHT)
    tris, cols = [], []
    for shape, color in items:
        verts, idx = shape.tessellate(tol, 0.2)
        if not idx:
            continue
        tri = np.array([(q.X, q.Y, q.Z) for q in verts])[np.array(idx)]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        nl = np.linalg.norm(n, axis=1)
        keep = nl > 1e-12
        tri, n = tri[keep], n[keep] / nl[keep, None]
        n = np.where((n @ v)[:, None] < 0, -n, n)  # two-sided
        shade = 0.3 + 0.7 * np.clip(n @ light, 0, 1)
        tris.append(tri)
        cols.append(np.clip(np.outer(shade, _rgb(color)), 0, 1))
    tri = np.concatenate(tris)
    col = (np.concatenate(cols) * 255).astype(np.uint8)
    x, y, z = tri @ xr, tri @ yr, tri @ v
    span = max(x.max() - x.min(), y.max() - y.min()) * 1.04
    sc = px / span
    ox = (px - (x.max() - x.min()) * sc) / 2
    oy = (px - (y.max() - y.min()) * sc) / 2
    sx = (x - x.min()) * sc + ox
    sy = px - ((y - y.min()) * sc + oy)
    zbuf = np.full((px, px), -1e18)
    img = np.empty((px, px, 3), np.uint8)
    img[:] = bg
    _raster(sx, sy, z, col, px, zbuf, img)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img).save(path)
