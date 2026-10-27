"""The one shape everything is made of: a tube of vertical sections, each an ellipse above (what you see) and below
it a fill running in to the bed at 45 degrees or steeper (hidden under the round). Nothing overhangs, so the sprig
prints flat-back with no supports. Meshes straight from the points: B-rep booleans gave up on freeform petals.
"""
import math

import numpy as np

from cadkit.mesh import Mesh

ARC = 49  # points round each section's ellipse: odd, so one sits on top (flat tops land on layers)
FILL = 6  # points down each side of the fill and along the bed
FLOOR = 0.4  # an ellipse that dips under the bed stops this high, and its fill runs in from there
STEEP = 50.0  # deg from level: where the round hands over to the fill (45 prints; the margin covers the chords)
TAIL = 46.0  # deg from level: the fill's sides (45 prints; a degree's margin so float error never tips them over)
FOOT = 0.9  # the fill's foot is at least this share of its top's width: two lines on a pedicel, and stiffer



def bezier(pts, n: int) -> np.ndarray:
    """n points along the Bezier curve through pts' end points (pulled toward the middle ones)."""
    pts = np.asarray(pts, float)
    t = np.linspace(0, 1, n)[:, None]
    k = len(pts) - 1
    return sum(math.comb(k, i) * (1 - t) ** (k - i) * t ** i * pts[i] for i in range(k + 1))


def section(r: float, zc: float, flat: float = 1.0, lobe=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(w, z, theta): a closed counter-clockwise section across a tube, w sideways, z up from the bed. The ellipse
    (half-width r, half-height r * flat, centred zc) over the top, down each side until its underside gets flatter
    than STEEP (or reaches FLOOR); then straight in to the bed (TAIL or steeper), along it and back up.
    lobe(theta) scales the radius round the ellipse (symmetric about the top). theta is NaN on the fill."""
    def curve(th):
        rr = r * (lobe(th) if lobe else 1.0)
        return rr * np.cos(th), zc + rr * flat * np.sin(th)

    # down from the widest, the ellipse (lobed or not) until its underside gets flatter than STEEP or nears the bed
    th = np.linspace(0, -math.pi / 2, 400)
    w, z = curve(th)
    bad = (-np.diff(w) > np.tan(math.radians(90 - STEEP)) * -np.diff(z)) | (z[1:] < FLOOR)
    start = th[np.argmax(bad)] if bad.any() else th[-1]
    th = np.linspace(start, math.pi - start, ARC)
    w, z = curve(th)
    (wr, zr), (wl, zl) = (w[0], z[0]), (w[-1], z[-1])
    run = 1 / math.tan(math.radians(TAIL))
    br, bl = max(wr - zr * run, FOOT * wr), min(wl + zl * run, FOOT * wl)  # where each side meets the bed
    s = np.linspace(0, 1, FILL)
    fw = np.concatenate([wl + (bl - wl) * s[1:], bl + (br - bl) * s[1:-1], br + (wr - br) * s[:-1]])
    fz = np.concatenate([zl * (1 - s[1:]), np.zeros(FILL - 2), zr * s[:-1]])
    return np.r_[w, fw], np.r_[z, fz], np.r_[th, np.full(len(fw), np.nan)]


def dome(r: float, h: float) -> tuple[np.ndarray, np.ndarray]:
    """(w, z): a closed counter-clockwise half-oval standing on the bed, half-width r and h tall: its round comes
    down to the wall upright, no band under it. As many points as a section, so the rings line up."""
    th = np.linspace(0, math.pi, ARC)
    bed = 3 * FILL - 4
    z = h * np.sin(th)
    z[[0, -1]] = 0.0  # sin(pi) is not quite 0
    return np.r_[r * np.cos(th), np.linspace(-r, r, bed + 2)[1:-1]], np.r_[z, np.zeros(bed)]


def tube(rings, label: str = "", ends=None) -> Mesh:
    """A closed mesh from rings [k][n][3] (each a closed loop, all the same n, lined up), capped at both ends by a
    fan from each end ring's centre (or from the two points `ends`)."""
    rings = np.asarray(rings, float)
    k, n, _ = rings.shape
    idx = np.arange(k * n).reshape(k, n)
    a, b = idx[:-1], np.roll(idx, -1, axis=1)[:-1]
    c, d = np.roll(idx, -1, axis=1)[1:], idx[1:]
    tris = [np.stack([a, b, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)]
    hub = k * n + np.arange(2)
    j, j1 = np.arange(n), (np.arange(n) + 1) % n
    tris.append(np.stack([np.full(n, hub[0]), idx[0, j1], idx[0, j]], 1))
    tris.append(np.stack([np.full(n, hub[1]), idx[-1, j], idx[-1, j1]], 1))
    centres = ends if ends is not None else (rings[0].mean(axis=0), rings[-1].mean(axis=0))
    verts = np.vstack([rings.reshape(-1, 3), *centres])
    m = Mesh(verts, np.concatenate(tris), label)
    return m if m.volume >= 0 else Mesh(m.verts, m.tris[:, ::-1], label)


def _along(path, sections, label: str) -> Mesh:
    """A tube along a plan path (m, 2) through one (w, z) section per point, each square to the path."""
    path = np.asarray(path, float)
    tang = np.gradient(path, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    side = np.stack([-tang[:, 1], tang[:, 0]], 1)
    return tube([np.stack([p[0] + w * s[0], p[1] + w * s[1], z], 1) for p, s, (w, z) in zip(path, side, sections)],
                label)


def sweep(path, r, zc, flat: float = 1.0, label: str = "") -> Mesh:
    """A tube of sections (round above, the fill under) along a plan path: radius r and centre height zc per
    point (or one for all)."""
    m = len(path)
    return _along(path, [section(ri, zi, flat)[:2] for ri, zi in zip(np.broadcast_to(r, m), np.broadcast_to(zc, m))],
                  label)


def sweep_dome(path, r, h, label: str = "") -> Mesh:
    """A tube of domes along a plan path: half-width r and height h per point (or one for all)."""
    m = len(path)
    return _along(path, [dome(ri, hi) for ri, hi in zip(np.broadcast_to(r, m), np.broadcast_to(h, m))], label)
