"""Flat colored previews of the front (top faces) and back (bed faces), plus a shaded 3/4 view."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from .params import P, Params  # noqa: E402


def _faces(bodies: dict, p: Params, up: bool):
    """[(z, rgb, [tri xy arrays])] for faces pointing +Z (front) or -Z (back)."""
    out = []
    for c, body in bodies.items():
        rgb = getattr(p, c)
        for f in body.faces():
            n = f.normal_at()
            if (n.Z > 0.99) if up else (n.Z < -0.99):
                verts, tris = f.tessellate(0.02, 0.1)
                xy = np.array([(v.X, v.Y) for v in verts])
                if not up:
                    xy[:, 0] *= -1  # seen from behind
                out.append((f.center().Z, rgb, [xy[list(t)] for t in tris]))
    out.sort(key=lambda t: t[0] if up else -t[0])
    return out


def flat(bodies: dict, path: str, p: Params = P, up: bool = True, px: int = 2400, bg="white"):
    from build123d import Compound

    bb = Compound(children=list(bodies.values())).bounding_box()
    x0, x1, y0, y1 = bb.min.X - 1.5, bb.max.X + 1.5, bb.min.Y - 1.5, bb.max.Y + 1.5
    if not up:
        x0, x1 = -x1, -x0
    fig = plt.figure(figsize=(px / 200, px / 200 * (y1 - y0) / (x1 - x0)), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)
    for _, rgb, polys in _faces(bodies, p, up):
        ax.add_collection(PolyCollection(polys, facecolors=[rgb], edgecolors=[rgb], linewidths=0.15))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(path, facecolor=bg)
    plt.close(fig)


def iso(bodies: dict, path: str, p: Params = P, px: int = 1400, elev: float = 35, azim: float = -60):
    """Painter's-algorithm shaded view; good enough to judge relief steps."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    light = np.array([-0.4, -0.6, 0.7])
    light /= np.linalg.norm(light)
    tris, cols = [], []
    for c, body in bodies.items():
        rgb = np.array(getattr(p, c))
        verts, faces = body.tessellate(0.05, 0.2)
        V = np.array([(v.X, v.Y, v.Z) for v in verts])
        for t in faces:
            tri = V[list(t)]
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            nn = np.linalg.norm(n)
            if nn < 1e-12:
                continue
            shade = 0.45 + 0.55 * max(0.0, float(np.dot(n / nn, light)))
            tris.append(tri)
            cols.append(np.clip(rgb * shade, 0, 1))
    fig = plt.figure(figsize=(px / 200, px / 200), dpi=200)
    ax = fig.add_subplot(projection="3d", computed_zorder=False)
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cols, edgecolors="none"))
    ax.set_xlim(-26, 26)
    ax.set_ylim(-24, 30)
    ax.set_zlim(-20, 24)
    ax.set_box_aspect((52, 54, 44))
    ax.view_init(elev=elev, azim=azim)
    ax.axis("off")
    fig.savefig(path, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def decode_qr(path: str) -> str:
    import cv2

    img = cv2.imread(path)
    text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    return text
