"""The logo raster (embedded in art/logo.svg) classified into palette colors and measured in mm.

Frame: origin at the ring center, +X right, +Y up (image rows run down, so y is negated)."""
import base64
import re
from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

from .params import ART, P, Params

# filament ids in the fil map (0 = outside the logo)
ORANGE, YELLOW, WHITE, BROWN = 1, 2, 3, 4
NAMES = {ORANGE: "orange", YELLOW: "yellow", WHITE: "white", BROWN: "brown"}

# art palette (sRGB hex) -> (class name, filament). Classes keep their identity for the design (ring vs cat
# orange, backdrop cream vs cat white); filaments are what gets printed.
PALETTE = [
    ("ring", "fab713", ORANGE),
    ("ribbon", "fef111", YELLOW),
    ("fold", "c7a811", YELLOW),
    ("fold_dark", "866408", YELLOW),
    ("ink", "452602", BROWN),
    ("cat_white", "fef9f5", WHITE),
    ("cat_white2", "f1e8dd", WHITE),
    ("cat_tan", "d7ae8d", WHITE),
    ("cat_tan2", "f0e0d0", WHITE),
    ("cat_tan3", "d0b090", WHITE),
    ("cream", "dac9aa", WHITE),
    ("cat_orange", "e58f48", ORANGE),
    ("cat_orange2", "bb6f37", ORANGE),
    ("ear", "8b5934", ORANGE),
    ("pink", "e98c9c", BROWN),
    ("pink_light", "f0b0c0", WHITE),
    ("iris", "b0a060", BROWN),
]
CLASS = {name: i for i, (name, _, _) in enumerate(PALETTE)}
CAT_FILL = {CLASS[n] for n in ("cat_white", "cat_white2", "cat_tan", "cat_tan2", "cat_tan3", "cat_orange",
                                "cat_orange2", "ear", "pink", "pink_light", "iris")}
RIBBON_FILL = {CLASS[n] for n in ("ribbon", "fold", "fold_dark")}


@dataclass
class Art:
    cls: np.ndarray  # palette class per pixel
    fil: np.ndarray  # filament per pixel, 0 outside
    valid: np.ndarray  # inside the logo
    px_mm: float
    cx: float  # ring center, image px
    cy: float
    R: float  # ring outer radius, mm (outside of its brown outline)
    r: float  # backdrop disc radius, mm (edge of the cream, inside its brown outline)

    def to_mm(self, x, y):
        return (np.asarray(x, float) - self.cx) / self.px_mm, -(np.asarray(y, float) - self.cy) / self.px_mm

    def to_px(self, x, y):
        return np.asarray(x, float) * self.px_mm + self.cx, -np.asarray(y, float) * self.px_mm + self.cy

    def mm_grid(self):
        """(x, y) in mm for every pixel."""
        yy, xx = np.mgrid[:self.cls.shape[0], :self.cls.shape[1]]
        return self.to_mm(xx, yy)


def _disc_radius(cream: np.ndarray, cx: float, cy: float, px_mm: float) -> float:
    """Outer radius of the cream backdrop: the last 0.1 mm radial bin where cream still fills most of the ring
    (the cat covers the middle, so the fraction is of the bin's circumference, and 'most' is 30%)."""
    ys, xs = np.where(cream)
    d = np.hypot(xs - cx, ys - cy) / px_mm
    step = 0.1
    counts, edges = np.histogram(d, bins=np.arange(0, d.max() + step, step))
    mids = (edges[:-1] + edges[1:]) / 2
    frac = counts / (2 * np.pi * mids * step * px_mm * px_mm + 1e-9)
    filled = np.where(frac > 0.3)[0]
    return float(edges[filled.max() + 1])


def _rgba(path) -> tuple[np.ndarray, np.ndarray]:
    s = path.read_text()
    blobs = re.findall(r'xlink:href="data:image/png;base64,([^"]+)"', s)
    dec = [cv2.imdecode(np.frombuffer(base64.b64decode(b), np.uint8), cv2.IMREAD_UNCHANGED) for b in blobs]
    mask = next(d for d in dec if d.ndim == 2)
    rgb = cv2.cvtColor(next(d for d in dec if d.ndim == 3), cv2.COLOR_BGR2RGB)
    return rgb, mask


def classify(rgb: np.ndarray, valid: np.ndarray, px_mm: float, sigma_mm: float = 0.03) -> np.ndarray:
    """Nearest palette color in Lab, then a small mode filter that removes anti-aliasing fringes."""
    pal = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for _, h, _ in PALETTE], np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_p = cv2.cvtColor(pal.reshape(1, -1, 3), cv2.COLOR_RGB2LAB).astype(np.float32)[0]
    best = np.zeros(rgb.shape[:2], np.uint8)
    best_d = np.full(rgb.shape[:2], np.inf, np.float32)
    for k, c in enumerate(lab_p):
        d = ((lab - c) ** 2).sum(-1)
        better = d < best_d
        best[better], best_d[better] = k, d[better]
    scores = np.stack([cv2.GaussianBlur((best == k).astype(np.float32), (0, 0), sigma_mm * px_mm)
                       for k in range(len(PALETTE))])
    out = scores.argmax(0).astype(np.uint8)
    out[~valid] = 0
    return out


@lru_cache(maxsize=2)
def load(p: Params = P) -> Art:
    rgb, mask = _rgba(ART)
    valid = mask > 128
    ys, xs = np.where(valid)
    px_mm = (xs.max() - xs.min()) / p.width
    cls = classify(rgb, valid, px_mm)
    fil = np.array([0] + [f for _, _, f in PALETTE], np.uint8)[np.where(valid, cls + 1, 0)]
    oy, ox = np.where(cls == CLASS["ring"])
    cx, cy = (ox.min() + ox.max()) / 2, (oy.min() + oy.max()) / 2
    # outer radius: the logo's edge in the top half is the ring's outline
    top = valid[: int(cy)]
    ty, tx = np.where(top)
    R = np.hypot(tx - cx, ty - cy).max() / px_mm
    r = _disc_radius(cls == CLASS["cream"], cx, cy, px_mm)
    return Art(cls, fil, valid, px_mm, cx, cy, R, r)
