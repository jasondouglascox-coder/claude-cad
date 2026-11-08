"""PNG previews: black vinyl on white, the way the sheet looks after weeding."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402

from .shapes import pieces  # noqa: E402


def _patch(shape, **kw):
    rings = [r for q in pieces(shape) for r in (q.exterior, *q.interiors)]
    verts, codes = [], []
    for r in rings:
        xy = list(r.coords)
        verts += xy
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
    return PathPatch(MPath(verts, codes), **kw)


def draw(ax, shapes, labels=None, edge=None):
    for i, s in enumerate(shapes):
        ax.add_patch(_patch(s, facecolor="black", edgecolor="none"))
        if labels:
            x0, y0, x1, _ = s.bounds
            ax.text((x0 + x1) / 2, y0 - 0.08, labels[i], ha="center", va="top", fontsize=8)
    ax.set_aspect("equal")
    ax.axis("off")


def poses(path, cats, cols=4):
    """Every pose on its own tile, labelled."""
    names = list(cats)
    rows = -(-len(names) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
    for ax, n in zip(axes.flat, names):
        draw(ax, [cats[n]])
        ax.set_title(n.replace("_", " "), fontsize=11)
        x0, y0, x1, y1 = cats[n].bounds
        ax.set_xlim(x0 - 0.15, x0 + 3.15)
        ax.set_ylim(y0 - 0.15, y0 + 3.15)
    for ax in list(axes.flat)[len(names):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def sheet(path, shapes, mat):
    """The whole mat, its edge drawn in grey."""
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.add_patch(plt.Rectangle((0, 0), *mat, fill=False, edgecolor="0.6"))
    draw(ax, shapes)
    ax.set_xlim(-0.2, mat[0] + 0.2)
    ax.set_ylim(-0.2, mat[1] + 0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
