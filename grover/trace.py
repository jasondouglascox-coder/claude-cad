"""Logo artwork (raster embedded in art/logo.svg) -> per-pixel art-color and zone maps.

Only light cleanup happens here (no morphological openings, which round off corners);
geometry is made crisp in design.py, in vector form.
"""

import base64
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

from .params import P, Params

ART = Path(__file__).resolve().parent.parent / "art" / "logo.svg"

FILAMENTS = ("orange", "yellow", "white", "brown")  # label ids 1..4; 0 = empty
ZONES = ("disk", "tail", "ring", "banner", "cat")  # ids ascending height: tails tuck under the ring

# art color -> (filament, zone). zone None = linework, resolved from neighbours.
PALETTE = [
    ("fab713", "orange", "ring"),  # gold ring -> Grover orange
    ("fef111", "yellow", "banner"),
    ("c7a811", "yellow", "tail"),  # ribbon folds
    ("866408", "yellow", "tail"),
    ("452602", "brown", None),
    ("fef9f5", "white", "cat"),
    ("f1e8dd", "white", "cat"),
    ("d7ae8d", "white", "cat"),
    ("dac9aa", "white", "disk"),  # beige backdrop -> white
    ("e58f48", "orange", "cat"),
    ("bb6f37", "orange", "cat"),
    ("8b5934", "orange", None),  # ear interiors; also anti-aliased brown-on-gold edges
    ("e98c9c", "brown", "cat"),  # pink nose/tongue -> brown so the nose reads
]


@dataclass
class Maps:
    fil: np.ndarray  # filament label per pixel (art colors mapped), 0 = empty
    zone: np.ndarray  # zone label per pixel, 0 = empty
    px_mm: float

    def to_mm(self, x, y):
        """Image pixel coords -> mm (y up). Origin is arbitrary; design.py recenters on the ring."""
        return np.asarray(x) / self.px_mm, -np.asarray(y) / self.px_mm


@lru_cache(maxsize=2)
def _art_rgba(path: str = str(ART)) -> np.ndarray:
    s = Path(path).read_text()
    imgs = re.findall(r'xlink:href="data:image/png;base64,([^"]+)"', s)
    dec = [cv2.imdecode(np.frombuffer(base64.b64decode(b), np.uint8), cv2.IMREAD_UNCHANGED) for b in imgs]
    mask = next(d for d in dec if d.ndim == 2)
    rgb = cv2.cvtColor(next(d for d in dec if d.ndim == 3), cv2.COLOR_BGR2RGB)
    return np.dstack([rgb, mask])


def disk_kernel(r_px: float) -> np.ndarray:
    r = max(1, int(round(r_px)))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return ((x * x + y * y) <= r_px * r_px + 0.5).astype(np.uint8)


def nearest_fill(lab: np.ndarray, keep: np.ndarray) -> np.ndarray:
    if keep.all():
        return lab
    _, (iy, ix) = ndi.distance_transform_edt(~keep, return_indices=True)
    return lab[iy, ix]


def _mode_filter(lab: np.ndarray, n: int, sigma: float, valid: np.ndarray) -> np.ndarray:
    scores = np.stack([cv2.GaussianBlur((lab == k).astype(np.float32), (0, 0), sigma) for k in range(1, n + 1)])
    out = (scores.argmax(0) + 1).astype(np.uint8)
    out[~valid] = 0
    return out


def _drop_specks(lab: np.ndarray, n: int, valid: np.ndarray, min_area_px: float) -> np.ndarray:
    keep = valid.copy()
    for k in range(1, n + 1):
        cc, num = ndi.label(lab == k)
        if num:
            sizes = ndi.sum(np.ones_like(cc), cc, range(1, num + 1))
            keep &= ~np.isin(cc, np.nonzero(sizes < min_area_px)[0] + 1)
    out = nearest_fill(np.where(keep, lab, 0), keep | ~valid)
    out[~valid] = 0
    return out


def _classify(img: np.ndarray) -> np.ndarray:
    lab_img = cv2.cvtColor(img[..., :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    pal_rgb = np.uint8([[[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h, _, _ in PALETTE]])
    pal_lab = cv2.cvtColor(pal_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)[0]
    best = np.full(lab_img.shape[:2], np.inf, np.float32)
    art = np.zeros(lab_img.shape[:2], np.int32)
    for i, c in enumerate(pal_lab):
        d = ((lab_img - c) ** 2).sum(-1)
        better = d < best
        best[better], art[better] = d[better], i
    return art


@lru_cache(maxsize=4)
def maps(p: Params = P) -> Maps:
    rgba = _art_rgba()
    a = rgba[..., 3]
    ys, xs = np.nonzero(a > 127)
    pad = 20
    crop = rgba[ys.min() - pad:ys.max() + pad, xs.min() - pad:xs.max() + pad]
    px_mm = p.px_mm
    scale = p.width * px_mm / (xs.max() - xs.min())
    size = (int(round(crop.shape[1] * scale)), int(round(crop.shape[0] * scale)))
    img = cv2.resize(crop, size, interpolation=cv2.INTER_AREA)
    valid = ndi.binary_fill_holes(img[..., 3] > 127)

    art = _classify(img)
    fil_of = np.array([FILAMENTS.index(f) + 1 for _, f, _ in PALETTE], np.uint8)
    zone_of = np.array([ZONES.index(z) + 1 if z else 0 for _, _, z in PALETTE], np.uint8)
    fil = np.where(valid, fil_of[art], 0).astype(np.uint8)
    zone = np.where(valid, zone_of[art], 0).astype(np.uint8)
    Z = {z: ZONES.index(z) + 1 for z in ZONES}
    nz = len(ZONES)

    fil = _mode_filter(fil, 4, p.mode_sigma * px_mm, valid)

    # Anti-aliased fringes (thin strips of the wrong color along linework) become linework.
    for k in range(1, nz + 1):
        m = (zone == k).astype(np.uint8)
        opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, disk_kernel(p.fringe * px_mm / 2)) > 0
        zone[(m > 0) & ~opened] = 0
    line = (zone == 0) & valid

    # Tails = banner-colored pieces outside the main ribbon face (letter counters stay banner).
    cc, num = ndi.label(zone == Z["banner"])
    if num > 1:
        sizes = ndi.sum(np.ones_like(cc), cc, range(1, num + 1))
        main = cc == sizes.argmax() + 1
        near_main = cv2.dilate(main.astype(np.uint8), disk_kernel(1.0 * px_mm)) > 0
        face = ndi.binary_fill_holes(main | (line & near_main))
        zone[(cc > 0) & ~face] = Z["tail"]

    # Linework joins the highest zone it touches (ids ascend with height), so each art
    # outline belongs to the raised side; deeper linework takes the nearest zone.
    near = ndi.maximum_filter(np.where(line, 0, zone), footprint=disk_kernel(p.line_reach * px_mm))
    zone = np.where(line, near, zone).astype(np.uint8)
    zone = nearest_fill(zone, (zone > 0) | ~valid)
    zone[~valid] = 0
    zone = _mode_filter(zone, nz, p.zone_sigma * px_mm, valid)
    zone = _drop_specks(zone, nz, valid, p.min_zone_area * px_mm ** 2)
    return Maps(fil=fil, zone=zone, px_mm=px_mm)


def preview(m: Maps, path: str, what: str = "fil", p: Params = P):
    if what == "fil":
        cols = [(255, 255, 255)] + [tuple(int(255 * c) for c in getattr(p, f)) for f in FILAMENTS]
        lab = m.fil
    else:
        cols = [(255, 255, 255), (220, 220, 220), (240, 140, 40), (200, 180, 30), (250, 240, 20),
                (90, 160, 220)]
        lab = m.zone
    img = np.array(cols, np.uint8)[lab]
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
