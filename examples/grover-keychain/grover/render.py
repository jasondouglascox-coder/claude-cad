"""Flat colored previews of the 2D design (fast) and of the solids' sections (what actually prints)."""
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from .params import P, Params  # noqa: E402


def _patch(poly, color):
    verts, codes = [], []
    for ring in (poly.exterior, *poly.interiors):
        c = list(ring.coords)
        verts += c
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", lw=0)


def draw(layers, path: Path, p: Params = P, bg="#808080", px_per_mm: int = 20, mirror: bool = False):
    """layers: [(color name, MultiPolygon)] painted in order (later on top)."""
    xs, ys = [], []
    for _, g in layers:
        if not g.is_empty:
            b = g.bounds
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
    x0, x1, y0, y1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    fig = plt.figure(figsize=((x1 - x0) * px_per_mm / 100, (y1 - y0) * px_per_mm / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(bg)
    for name, g in layers:
        for poly in (g.geoms if hasattr(g, "geoms") else [g]):
            ax.add_patch(_patch(poly, p.colors[name]))
    ax.set_xlim((x1, x0) if mirror else (x0, x1))
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, facecolor=bg)
    plt.close(fig)


def front_layers(d) -> list:
    from .regions import band_regions
    return [(c, g) for c, _, _, g in band_regions(d)]
