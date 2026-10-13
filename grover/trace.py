"""Turn the logo artwork (raster embedded in art/logo.svg) into printable color/height maps.

Pipeline (all in pixels at p.px_mm, origin = image top-left until `to_mm`):
  1. decode the embedded RGB image + luminance mask -> RGBA
  2. nearest-palette classification (Lab) -> art color index
  3. each art color maps to a filament and a zone (ring/disk/cat/banner/tail);
     brown linework takes the highest zone it touches, so outlines ride the raised side
  4. cleanup: mode filter, drop features thinner than the nozzle can print, drop specks
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
ZONES = ("disk", "ring", "tail", "cat", "banner", "paw")  # label ids 1..6; 0 = empty

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
    ("8b5934", "orange", None),  # ear interiors; also anti-aliased edges of brown on gold
    ("e98c9c", "brown", "cat"),  # pink nose/tongue -> brown so the nose reads
]


@dataclass
class Maps:
    fil: np.ndarray  # uint8 filament label per pixel
    zone: np.ndarray  # uint8 zone label per pixel
    px_mm: float
    origin: tuple  # (x0, y0) pixel of mm origin (image coords)
    hole_px: tuple  # keyring hole center (image coords)

    @property
    def hole_mm(self):
        return self.to_mm(*self.hole_px)

    def to_mm(self, x, y):
        return (x - self.origin[0]) / self.px_mm, (self.origin[1] - y) / self.px_mm


@lru_cache(maxsize=2)
def _art_rgba(path: str = str(ART)) -> np.ndarray:
    s = Path(path).read_text()
    imgs = re.findall(r'xlink:href="data:image/png;base64,([^"]+)"', s)
    dec = [cv2.imdecode(np.frombuffer(base64.b64decode(b), np.uint8), cv2.IMREAD_UNCHANGED) for b in imgs]
    mask = next(d for d in dec if d.ndim == 2)
    rgb = cv2.cvtColor(next(d for d in dec if d.ndim == 3), cv2.COLOR_BGR2RGB)
    return np.dstack([rgb, mask])


def _disk(r_px: float) -> np.ndarray:
    r = max(1, int(round(r_px)))
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r_px * r_px + 0.5


def _nearest_fill(lab: np.ndarray, keep: np.ndarray) -> np.ndarray:
    """Replace pixels where keep is False with the nearest kept label."""
    if keep.all():
        return lab
    _, (iy, ix) = ndi.distance_transform_edt(~keep, return_indices=True)
    return lab[iy, ix]


def _mode_filter(lab: np.ndarray, n: int, sigma: float, valid: np.ndarray) -> np.ndarray:
    scores = np.stack([cv2.GaussianBlur((lab == k).astype(np.float32), (0, 0), sigma) for k in range(1, n + 1)])
    out = (scores.argmax(0) + 1).astype(np.uint8)
    out[~valid] = 0
    return out


def _clean(lab: np.ndarray, n: int, valid: np.ndarray, min_w: dict, min_area, px_mm: float) -> np.ndarray:
    """Drop features thinner than min_w[k] mm and specks under min_area mm^2; refill from neighbours."""
    keep = valid.copy()
    for k in range(1, n + 1):
        m = lab == k
        w = min_w.get(k, 0)
        if w > 0:
            opened = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, _disk(w * px_mm / 2).astype(np.uint8)) > 0
            keep &= ~(m & ~opened)
            m = opened
        cc, num = ndi.label(m)
        if num:
            sizes = ndi.sum(m, cc, range(1, num + 1)) / px_mm ** 2
            a = min_area.get(k, 0) if isinstance(min_area, dict) else min_area
            small = np.isin(cc, np.nonzero(sizes < a)[0] + 1)
            keep &= ~small
    out = _nearest_fill(np.where(keep, lab, 0), keep | ~valid)
    out[~valid] = 0
    return out


@lru_cache(maxsize=4)
def maps(p: Params = P) -> Maps:
    rgba = _art_rgba()
    a = rgba[..., 3]
    ys, xs = np.nonzero(a > 127)
    pad = 20
    x0, x1, y0, y1 = xs.min() - pad, xs.max() + pad, ys.min() - pad, ys.max() + pad
    crop = rgba[y0:y1, x0:x1]
    art_w_px = xs.max() - xs.min()
    px_mm = p.px_mm
    scale = p.width * px_mm / art_w_px
    size = (int(round(crop.shape[1] * scale)), int(round(crop.shape[0] * scale)))
    img = cv2.resize(crop, size, interpolation=cv2.INTER_AREA)
    valid = img[..., 3] > 127
    valid = ndi.binary_fill_holes(valid)

    # 1. classify in Lab
    lab_img = cv2.cvtColor(img[..., :3], cv2.COLOR_RGB2LAB).astype(np.float32)
    pal_rgb = np.uint8([[[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h, _, _ in PALETTE]])
    pal_lab = cv2.cvtColor(pal_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)[0]
    d = ((lab_img[:, :, None, :] - pal_lab[None, None]) ** 2).sum(-1)
    art = d.argmin(-1)

    fil_of = np.array([FILAMENTS.index(f) + 1 for _, f, _ in PALETTE], np.uint8)
    zone_of = np.array([ZONES.index(z) + 1 if z else 0 for _, _, z in PALETTE], np.uint8)
    fil = np.where(valid, fil_of[art], 0).astype(np.uint8)
    zone = np.where(valid, zone_of[art], 0).astype(np.uint8)
    Z = {z: ZONES.index(z) + 1 for z in ZONES}
    nz = len(ZONES)

    # 2. zones. Tails = banner-colored pieces other than the main ribbon face
    #    (computed before linework joins them together).
    # anti-aliased fringes (thin strips of the wrong color around linework) become linework
    for k in range(1, nz + 1):
        m = (zone == k).astype(np.uint8)
        opened = cv2.morphologyEx(m, cv2.MORPH_OPEN, _disk(p.fringe * px_mm / 2).astype(np.uint8)) > 0
        zone[(m > 0) & ~opened] = 0
    line = (zone == 0) & valid
    cc, num = ndi.label(zone == Z["banner"])
    if num > 1:
        sizes = ndi.sum(np.ones_like(cc), cc, range(1, num + 1))
        main = cc == sizes.argmax() + 1
        near_main = cv2.dilate(main.astype(np.uint8), _disk(1.0 * px_mm).astype(np.uint8)) > 0
        face = ndi.binary_fill_holes(main | (line & near_main))  # letter counters stay banner
        zone[(cc > 0) & ~face] = Z["tail"]
    near = ndi.maximum_filter(np.where(line, 0, zone), footprint=_disk(p.line_reach * px_mm))
    zone = np.where(line, near, zone).astype(np.uint8)
    zone = _nearest_fill(zone, (zone > 0) | ~valid)
    zone[~valid] = 0
    zone = _mode_filter(zone, nz, p.zone_sigma * px_mm, valid)
    zone = _clean(zone, nz, valid, {k: p.min_zone_width for k in range(1, nz + 1)}, p.min_zone_area, px_mm)
    zone[_paws(zone, Z, p, px_mm)] = Z["paw"]

    # 3. filaments: smooth, keep only brown art features thick enough to print,
    #    then outline every relief step on its raised side.
    b = FILAMENTS.index("brown") + 1
    fil = _mode_filter(fil, 4, p.mode_sigma * px_mm, valid)
    fil = _clean(fil, 4, valid, {b: p.min_line}, 0, px_mm)
    shrunk = cv2.erode((fil == b).astype(np.uint8), _disk(p.brown_shrink * px_mm).astype(np.uint8)) > 0
    fil = _nearest_fill(fil, (fil != b) | shrunk | ~valid)
    fil[~valid] = 0
    top_paw, (hx, _) = _top_paw(fil, zone, Z, px_mm)
    fil[top_paw] = FILAMENTS.index("orange") + 1
    col = int(round(hx))
    top_row = np.argmax(valid[:, col])
    hole = (hx, top_row + (p.hole_wall + p.hole_r) * px_mm)  # wall measured to the outer edge
    h = np.array([0.0] + [p.zone_top[z] for z in ZONES], np.float32)[zone]
    lower_near = ndi.minimum_filter(h, footprint=_disk(p.line_w * px_mm)) < h - 1e-3
    fil[lower_near & valid] = b
    fil = _clean(fil, 4, valid, {k: p.min_feature for k in range(1, 4)} | {b: p.min_line},
               {FILAMENTS.index(f) + 1: a for f, a in p.min_areas}, px_mm)

    y, x = np.mgrid[:fil.shape[0], :fil.shape[1]]
    near_hole = np.hypot(x - hole[0], y - hole[1]) / px_mm <= p.hole_r + p.line_w
    fil[near_hole] = b
    zone[near_hole] = Z["ring"]

    # mm origin: ring center
    ring = zone == ZONES.index("ring") + 1
    ry, rx = np.nonzero(ring)
    cx, cy = (rx.min() + rx.max()) / 2, (ry.min() + ry.max()) / 2
    return Maps(fil=fil, zone=zone, px_mm=px_mm, origin=(cx, cy), hole_px=hole)


def _paws(zone, Z, p: Params, px_mm: float) -> np.ndarray:
    """Cat pixels that hang below the banner's top arc (the paws resting on it)."""
    ban = zone == Z["banner"]
    cat = zone == Z["cat"]
    cols = np.nonzero(ban.any(0))[0]
    top = np.argmax(ban[:, cols], axis=0)
    above_is_cat = cat[np.clip(top - 2, 0, None), cols]
    xs, ys = cols[~above_is_cat], top[~above_is_cat]
    a, bb, c = np.polyfit(xs, ys, 2)
    rows = np.arange(zone.shape[0])[:, None]
    x = np.arange(zone.shape[1])
    arc = (a * x * x + bb * x + c)[None, :]
    below = cat & (rows > arc)
    depth = below.sum(0)  # how far the cat hangs over the banner, per column
    paw_cols = cv2.dilate((depth > p.paw_depth * px_mm).astype(np.uint8)[None, :],
                          np.ones((1, int(0.6 * px_mm)), np.uint8))[0] > 0
    return cat & paw_cols[None, :] & (rows > arc - p.paw_lift * px_mm)


def _top_paw(fil, zone, Z, px_mm: float):
    """The ring paw print at 12 o'clock (toes + pad), which the keyring hole replaces."""
    b = FILAMENTS.index("brown") + 1
    ring = zone == Z["ring"]
    ry, rx = np.nonzero(ring)
    cx = (rx.min() + rx.max()) / 2
    # skip the ring's own edge linework; paw prints sit well inside the ring
    interior = ndi.distance_transform_edt(ring) > 0.9 * px_mm
    brown = (fil == b) & interior
    grouped = cv2.dilate(brown.astype(np.uint8), _disk(0.6 * px_mm).astype(np.uint8)) > 0
    cc, num = ndi.label(grouped)
    boxes = ndi.find_objects(cc)
    cents = ndi.center_of_mass(brown, cc, range(1, num + 1))

    def paw_like(i):
        h, w = (sl.stop - sl.start for sl in boxes[i])
        return all(2.5 * px_mm <= v <= 7 * px_mm for v in (h, w))

    cand = [i for i in range(num) if paw_like(i)]
    if not cand:
        raise ValueError(f"no paw print found in the ring for the keyring hole: {[(b[0].stop-b[0].start, b[1].stop-b[1].start) for b in boxes]}")
    top = min(cand, key=lambda i: abs(cents[i][1] - cx) + cents[i][0])
    hy, hx = cents[top]
    return (fil == b) & ring & (cc == top + 1), (hx, hy)


def preview(m: Maps, path: str, what: str = "fil", p: Params = P):
    if what == "fil":
        cols = [(255, 255, 255)] + [tuple(int(255 * c) for c in getattr(p, f)) for f in FILAMENTS]
        lab = m.fil
    else:
        cols = [(255, 255, 255), (220, 220, 220), (240, 140, 40), (200, 180, 30), (90, 160, 220), (250, 240, 20), (230, 60, 160)]
        lab = m.zone
    img = np.array(cols, np.uint8)[lab]
    cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
