"""The logo's dark line work, made printable: thick marks keep their shape, thin strokes become uniform lines.

Raster in, raster out (masks at the art's resolution); regions.py decides which marks go where."""
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from . import vec as V
from .params import P, Params


def split(ink: np.ndarray, px_mm: float, p: Params = P) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(thick, thin, kept): thick marks are at least ink_thick wide in the art and keep their traced shape; thin strokes
    are their centerlines re-stroked line_w wide. Strokes thinner than ink_min_src (whiskers) are dropped."""
    ink = V.closed(ink, 0.04 * px_mm)  # heal anti-aliasing nicks before measuring widths
    kept = V.opened(ink, p.ink_min_src / 2 * px_mm)
    thick = V.opened(kept, p.ink_thick / 2 * px_mm)
    sk = skeletonize(kept & ~V.dilated(thick, 0.05 * px_mm))
    sk = _trim_ends(sk, int(round(p.spur * px_mm)))
    sk = _prune(sk, min_len_px=p.ink_min_len * px_mm)
    thin = V.dilated(sk, p.line_w / 2 * px_mm)
    return thick, thin, kept


def _trim_ends(sk: np.ndarray, n: int) -> np.ndarray:
    """Peel n pixels off every free end: branches shorter than n (spurs from width wobble) vanish, real strokes
    get n px shorter (the round stroke cap gives most of it back)."""
    sk = sk.copy()
    for _ in range(n):
        s8 = np.pad(sk, 1).astype(np.uint8)
        nb = sum(s8[1 + dy:s8.shape[0] - 1 + dy, 1 + dx:s8.shape[1] - 1 + dx]
                 for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
        sk &= nb > 1
    return sk


def _prune(sk: np.ndarray, min_len_px: float) -> np.ndarray:
    """Drop skeleton fragments shorter than min_len (spurs left by the opening)."""
    lab, n = ndi.label(sk, structure=np.ones((3, 3)))
    if n == 0:
        return sk
    sizes = ndi.sum(sk, lab, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= min_len_px
    return keep[lab]
