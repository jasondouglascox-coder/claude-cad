"""The front design as 2D regions per print band, in mm, from the classified logo.

Raster work at the art's resolution, vectorized at the end. The figure (cat + ribbon + their ink) is moved down
by figure_drop; the ring, its circles and paw prints stay. Each band is a gap-free label map, so the regions of
one band tile it exactly and never overlap."""
from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPolygon, Point
from shapely.ops import unary_union

from . import art as A
from . import ink as I
from . import vec as V
from .params import P, Params

EMPTY, YELLOW, WHITE, ORANGE, BROWN = 0, 1, 2, 3, 4
LABEL = {YELLOW: "yellow", WHITE: "white", ORANGE: "orange", BROWN: "brown"}


@dataclass
class Design:
    silhouette: MultiPolygon
    hole: tuple  # (x, y, r)
    base_white: MultiPolygon
    base_orange: MultiPolygon
    ribbon: MultiPolygon  # face band, yellow
    cat_white: MultiPolygon
    cat_orange: MultiPolygon
    face_ink: MultiPolygon  # face band, brown, up to z_face
    ring_ink: MultiPolygon  # brown on the ring, up to z_ring_ink
    top_white: MultiPolygon  # paws, glints
    top_brown: MultiPolygon  # eyes, nose, letters, paw lines
    paws: MultiPolygon = None  # the two paw footprints (their lines included)
    eyes: list = field(default_factory=list)  # (x, y, r)
    figure_top: float = 0.0  # highest y of the figure (ear tips), mm
    R: float = 0.0
    r: float = 0.0
    masks: dict = field(default_factory=dict)  # named raster masks, for debugging and tests


def _shift(mask: np.ndarray, dy_px: int) -> np.ndarray:
    """Move a mask down the image by dy_px rows (down in the picture = -Y in mm)."""
    out = np.zeros_like(mask)
    out[dy_px:] = mask[:mask.shape[0] - dy_px]
    return out


def _fit_circle(mask: np.ndarray, art: A.Art) -> tuple:
    ys, xs = np.where(mask)
    (cx, cy), r = cv2.minEnclosingCircle(np.column_stack([xs, ys]).astype(np.float32))
    x, y = art.to_mm(cx, cy)
    return float(x), float(y), float(r / art.px_mm)


def _disc(shape, art: A.Art, x: float, y: float, r: float) -> np.ndarray:
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    ex, ey = art.to_px(x, y)
    return (xx - ex) ** 2 + (yy - ey) ** 2 <= (r * art.px_mm) ** 2


def _drop_islands(lab: np.ndarray, inside: np.ndarray, min_px: float) -> np.ndarray:
    """Fill pieces smaller than min_px join their neighbours (a nozzle can't print a fleck)."""
    out = lab.copy()
    for k in (YELLOW, WHITE, ORANGE):
        n, cc, stats, _ = cv2.connectedComponentsWithStats((lab == k).astype(np.uint8), connectivity=8)
        small = np.where(stats[1:, cv2.CC_STAT_AREA] < min_px)[0] + 1
        if len(small):
            out[np.isin(cc, small)] = EMPTY
    return _fill_nearest(out, inside)


def _minus(g, *higher, sliver: float = 0.02):
    """g minus every higher-priority region, without the hairline slivers a near-coincident boundary leaves."""
    out = g.difference(unary_union(list(higher))) if higher else g
    out = out.buffer(-0.01, join_style="mitre").buffer(0.01, join_style="mitre")
    return V.multi(unary_union([q for q in V.multi(out).geoms if q.area >= sliver]))


def _fill_nearest(lab: np.ndarray, inside: np.ndarray) -> np.ndarray:
    """Every unlabeled pixel inside takes the label of the nearest labeled pixel: no slivers between regions."""
    keep = lab > 0
    _, (iy, ix) = ndi.distance_transform_edt(~keep, return_indices=True)
    out = lab[iy, ix]
    out[~inside] = 0
    return out


@lru_cache(maxsize=2)
def design(p: Params = P) -> Design:
    art = A.load(p)
    px = art.px_mm
    cls = art.cls
    X, Y = art.mm_grid()
    D = np.hypot(X, Y)
    C = A.CLASS

    ink = cls == C["ink"]
    cat = np.isin(cls, list(A.CAT_FILL))
    ribbon = np.isin(cls, list(A.RIBBON_FILL))

    # --- figure vs background ink. Figure ink hugs the cat/ribbon fills; the two drawn circles are rebuilt.
    reach = V.dilated(cat | ribbon, 0.6 * px)
    hug = V.dilated(cat | ribbon, 0.25 * px)
    band = (np.abs(D - (art.r + p.circle_w / 2)) < p.circle_w / 2 + 0.15) | \
           (np.abs(D - (art.R - p.circle_w / 2)) < p.circle_w / 2 + 0.15)
    keep = V.dilated(ink & hug, 0.5 * px)  # the figure's outline crossing a circle, not the circle itself
    fig_ink = ink & reach & (~band | keep)
    bg_ink = ink & ~fig_ink

    # --- paw prints on the ring (thick marks between the circles); the top one becomes the hole
    ring_zone = (D > art.r + p.circle_w + 0.3) & (D < art.R - p.circle_w - 0.3)
    thick_bg, _, _ = I.split(bg_ink & ring_zone, px, p)
    paws_ring = np.zeros_like(ink)
    for c in V.components(thick_bg, int(0.5 * px * px)):
        ys, xs = np.where(c)
        x, y = art.to_mm(xs.mean(), ys.mean())
        if not (abs(x) < 2.0 and y > 0):  # all but the 12 o'clock print
            paws_ring |= c

    # --- the figure: cat + ribbon fills and ink, moved down
    dy = int(round(p.figure_drop * px))
    cat_mask, ribbon_mask, fig_ink = (_shift(m, dy) for m in (cat, ribbon, fig_ink))
    cls_s = _shift(cls, dy)
    thick, thin, kept = I.split(fig_ink, px, p)

    # pink: the nose is the top pink blob; the tongue and anything else turn white
    pink = cls_s == C["pink"]
    nose, best = np.zeros_like(pink), None
    for c in V.components(pink, int(0.3 * px * px)):
        y = art.to_mm(0, np.where(c)[0].mean())[1]
        if best is None or y > best:
            best, nose = y, c
    nose = V.closed(nose | (V.dilated(nose, 0.15 * px) & thick), 0.1 * px)
    tongue = V.dilated(pink & ~nose, 0.25 * px)
    thin &= ~tongue
    ink_print = thick | thin

    # eyes: round dark/iris blobs inside the cat, the two largest; glints are the white spots inside them
    eye_src = V.opened((cls_s == C["ink"]) | (cls_s == C["iris"]), 0.3 * px) & V.eroded(cat_mask | fig_ink, 0.2 * px)
    eyes, eye_mask, glints = [], np.zeros_like(pink), np.zeros_like(pink)
    white_cls = np.isin(cls_s, [C["cat_white"], C["cat_white2"]])
    for c in sorted(V.components(eye_src, int(2.0 * px * px)), key=lambda c: -c.sum()):
        if len(eyes) == 2:
            break
        x, y, r = _fit_circle(c, art)
        if r > 3.0 or c.sum() < 0.5 * np.pi * (r * px) ** 2:
            continue
        eyes.append((x, y, r))
        disc = _disc(cls.shape, art, x, y, r)
        eye_mask |= disc
        spots = sorted(V.components(white_cls & V.eroded(disc, 0.25 * px), int(0.05 * px * px)), key=lambda g: -g.sum())
        for g in spots[:2]:
            gx, gy, gr = _fit_circle(g, art)
            glints |= _disc(cls.shape, art, gx, gy, min(max(gr, p.eye_glint_min_d / 2), 0.35 * r))

    # --- face band label map: ribbon / cat white / cat orange / ink, gap-free inside the figure
    cat_region = np.zeros_like(pink)
    for c in V.components(V.closed(cat_mask | pink | (cls_s == C["iris"]) | ink_print, 0.1 * px),
                          int(p.cat_min_area * px * px)):
        cat_region |= c
    cat_fill = cat_region & ~ribbon_mask
    figure = np.zeros_like(pink)
    for c in V.components(V.closed(cat_fill | ribbon_mask | ink_print, 0.15 * px), int(p.cat_min_area * px * px)):
        figure |= ndi.binary_fill_holes(c)
    fig_top = float(art.to_mm(0, np.where(figure)[0].min())[1])
    cat_white = np.isin(cls_s, [C[n] for n in ("cat_white", "cat_white2", "cat_tan", "cat_tan2", "cat_tan3",
                                                 "pink_light")]) | (pink & ~nose)
    cat_white = V.opened(cat_white & cat_fill, p.fill_min / 2 * px)
    cat_orange = V.opened(cat_fill & ~cat_white, p.fill_min / 2 * px)
    lab = np.zeros(cls.shape, np.uint8)
    lab[V.opened(ribbon_mask, p.fill_min / 2 * px)] = YELLOW
    lab[cat_orange] = ORANGE
    lab[cat_white] = WHITE
    lab[ink_print | nose | eye_mask] = BROWN
    lab = _drop_islands(_fill_nearest(lab, figure), figure, p.min_island * px * px)

    # paws: the big white blobs at the ribbon. Closing the ink shuts the wrist gap that joins a paw to the
    # chest fur; the rim the closing ate is grown back from the white.
    paws = np.zeros_like(pink)
    near_ribbon = V.dilated(ribbon_mask, 1.0 * px)
    white = lab == WHITE
    core = white & ~V.closed(lab == BROWN, p.paw_close / 2 * px)
    for c in V.components(core, int(p.paw_min_area * px * px)):
        if (c & near_ribbon).any():
            paws |= white & V.dilated(c, p.paw_close / 2 * px + 2) & ~V.dilated(lab == YELLOW, 0.05 * px)
    paw_ink = (lab == BROWN) & V.dilated(paws, 0.4 * px) & ~eye_mask

    # letters: thick marks surrounded by ribbon yellow (the outline isn't; the cat's marks aren't)
    letters = np.zeros_like(pink)
    near = V.dilated(ribbon_mask, 2.0 * px)
    for c in V.components(V.opened(kept, 0.1 * px), int(0.5 * px * px)):
        if (c & ~near).any() or (c & cat_fill).any():
            continue
        rim = V.dilated(c, 0.35 * px) & ~c
        if (rim & ribbon_mask).sum() >= p.letter_surround * rim.sum():
            letters |= c

    # top band rests on the face band: under letters the face band is yellow, under paw lines white.
    # Splitting a line between bands leaves slivers; marks thinner than a line join the nearest fill.
    r_line = (p.line_w - 0.05) / 2 * px
    paw_ink = V.opened(paw_ink, r_line)
    letters = V.opened(letters, r_line)
    top_brown = (eye_mask & ~glints) | nose | letters | paw_ink
    top_white = (paws & ~paw_ink) | glints
    face = lab.copy()
    face_brown = V.opened((lab == BROWN) & ~letters & ~paw_ink, r_line) | eye_mask | nose
    face[(lab == BROWN) & ~face_brown] = EMPTY
    face = _drop_islands(_fill_nearest(face, figure), figure, p.min_island * px * px)
    face_ink = face == BROWN

    # --- base band and ring
    hole_r = p.hole_d / 2
    hole = (0.0, art.R - p.hole_wall - hole_r, hole_r)
    silhouette_m = (D <= art.R) | figure
    base_white = ((D <= art.r + p.circle_w) | V.dilated(figure, 0.1 * px)) & silhouette_m
    base_orange = silhouette_m & ~base_white
    outer_circle = silhouette_m & (D > art.R - p.circle_w)
    disc_circle = (D > art.r) & (D <= art.r + p.circle_w)
    ring_ink = (outer_circle | disc_circle | paws_ring) & ~V.dilated(figure, 0.05 * px)

    def poly(m):
        return V.mask_polys(m, art.to_mm, px, p.vec_smooth, p.vec_tol) if m.any() else MultiPolygon()

    # vectorize, then make each band's regions exactly disjoint (higher priority wins; the contours of
    # neighbouring masks differ by up to vec_tol, which would otherwise leave hairline overlaps)
    face_ink_g = poly(face_ink)
    cat_w_g = _minus(poly(face == WHITE), face_ink_g)
    cat_o_g = _minus(poly(face == ORANGE), face_ink_g, cat_w_g)
    ribbon_g = _minus(poly(face == YELLOW), face_ink_g, cat_w_g, cat_o_g)
    ring_ink_g = _minus(poly(ring_ink), face_ink_g, cat_w_g, cat_o_g, ribbon_g)
    top_brown_g = poly(top_brown)
    top_white_g = _minus(poly(top_white), top_brown_g)
    base_white_g = poly(base_white)
    base_orange_g = _minus(poly(base_orange), base_white_g)
    d = Design(
        silhouette=poly(silhouette_m), hole=hole,
        base_white=base_white_g, base_orange=base_orange_g,
        ribbon=ribbon_g, cat_white=cat_w_g, cat_orange=cat_o_g,
        face_ink=face_ink_g, ring_ink=ring_ink_g,
        top_white=top_white_g, top_brown=top_brown_g, paws=poly(paws | paw_ink),
        eyes=eyes, figure_top=fig_top, R=art.R, r=art.r,
        masks=dict(ink=ink, fig_ink=fig_ink, thick=thick, thin=thin, figure=figure, face=face, lab=lab,
                   face_ink=face_ink, ring_ink=ring_ink, top_white=top_white, top_brown=top_brown,
                   letters=letters, paws=paws, paw_ink=paw_ink, nose=nose, eye_mask=eye_mask, glints=glints,
                   base_white=base_white, base_orange=base_orange),
    )
    # the hole's brown ring sits on the orange base like a paw print
    hx, hy, hr = hole
    d.ring_ink = V.multi(unary_union([d.ring_ink, Point(hx, hy).buffer(hr + p.hole_ring_w, 64)]))
    return d


def band_regions(d: Design):
    """[(color, z0 name, z1 name, geometry)] for every printed region of the front."""
    return [
        ("white", "z_body", "z_base", d.base_white),
        ("orange", "z_body", "z_base", d.base_orange),
        ("yellow", "z_base", "z_face", d.ribbon),
        ("white", "z_base", "z_face", d.cat_white),
        ("orange", "z_base", "z_face", d.cat_orange),
        ("brown", "z_base", "z_face", d.face_ink),
        ("brown", "z_base", "z_ring_ink", d.ring_ink),
        ("white", "z_face", "z_top", d.top_white),
        ("brown", "z_face", "z_top", d.top_brown),
    ]
