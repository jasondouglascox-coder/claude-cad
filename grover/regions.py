"""The front design as 2D regions per print band, in mm, from the classified logo.

Raster work at the art's resolution, vectorized at the end. The figure (cat + ribbon + their ink) is moved down
by figure_drop; the ring, its circles and paw prints stay. Each band is a gap-free label map, so the regions of
one band tile it exactly and never overlap."""
from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPolygon, Point, box
from shapely.ops import unary_union

from . import art as A
from . import ears as E
from . import eyes as EY
from . import muzzle as MZ
from . import paws as PW
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
    top_white: MultiPolygon  # paws, eye crescents and glints
    top_brown: MultiPolygon  # eyes, nose, letters, paw lines
    paws: MultiPolygon = None  # the two paw footprints (their lines included)
    eyes: list = field(default_factory=list)  # (x, y, r)
    figure_top: float = 0.0  # highest y of the figure (ear tips), mm
    R: float = 0.0
    r: float = 0.0
    masks: dict = field(default_factory=dict)  # named raster masks, for debugging and tests


# ---- raster helpers ------------------------------------------------------------------------------------------

def _shift(mask: np.ndarray, dy_px: int) -> np.ndarray:
    """Move a mask down the image by dy_px rows (down in the picture = -Y in mm)."""
    out = np.zeros_like(mask)
    out[dy_px:] = mask[:mask.shape[0] - dy_px]
    return out


def _sweep_down(mask: np.ndarray, dy_px: int, step: int = 4) -> np.ndarray:
    """Union of the mask moved down by 0 .. dy_px."""
    out = mask.copy()
    for d in range(step, dy_px + 1, step):
        out |= _shift(mask, d)
    return out | _shift(mask, dy_px)


def _big(mask: np.ndarray, min_px: float) -> np.ndarray:
    out = np.zeros_like(mask)
    for c in V.components(mask, int(min_px)):
        out |= c
    return out


def _fill_nearest(lab: np.ndarray, inside: np.ndarray) -> np.ndarray:
    """Every unlabeled pixel inside takes the label of the nearest labeled pixel: no slivers between regions."""
    keep = lab > 0
    _, (iy, ix) = ndi.distance_transform_edt(~keep, return_indices=True)
    out = lab[iy, ix]
    out[~inside] = 0
    return out


def _drop_islands(lab: np.ndarray, inside: np.ndarray, min_px: float) -> np.ndarray:
    """Fill pieces smaller than min_px join their neighbours (a nozzle can't print a fleck)."""
    out = lab.copy()
    for k in (YELLOW, WHITE, ORANGE):
        n, cc, stats, _ = cv2.connectedComponentsWithStats((lab == k).astype(np.uint8), connectivity=8)
        small = np.where(stats[1:, cv2.CC_STAT_AREA] < min_px)[0] + 1
        if len(small):
            out[np.isin(cc, small)] = EMPTY
    return _fill_nearest(out, inside)


def _open_counters(m: np.ndarray, yellow: np.ndarray, min_d_px: float) -> np.ndarray:
    """A letter's counter (a hole in the mark, or yellow the classifier's smoothing swallowed inside it) narrower
    than min_d becomes a round hole of that diameter: a nozzle can't leave a thinner one open, and the G, & and A
    have to read."""
    inside = ndi.binary_fill_holes(m)
    holes = (inside & ~m) | (V.eroded(inside, min_d_px / 3) & yellow)  # edge pixels aren't counters
    out = m.copy()
    for c in V.components(holes, int(0.3 * (min_d_px / 2) ** 2)):
        if not V.opened(c, min_d_px / 2).any():  # too narrow somewhere
            ys, xs = np.where(c)
            (cx, cy), r = cv2.minEnclosingCircle(np.column_stack([xs, ys]).astype(np.float32))
            yy, xx = np.ogrid[:m.shape[0], :m.shape[1]]
            out &= ~((xx - cx) ** 2 + (yy - cy) ** 2 <= (max(r, min_d_px / 2)) ** 2)
    return out


def _stamp_around(stamp: np.ndarray, art: A.Art, radius: float, step_deg: float, scale: float = 1.0) -> list:
    """Copies of a paw print placed every step_deg around the ring at `radius`, skipping 12 o'clock (the hole), each
    turned so its palm faces the center and its toes point out. The copies are what print: the logo's prints sit
    at uneven radii and angles."""
    ys, xs = np.where(stamp)
    sx, sy = xs.mean(), ys.mean()
    pads = sorted(V.components(stamp), key=lambda c: -c.sum())  # the palm is the biggest pad
    py, px_ = np.where(pads[0])
    toes = np.array([[np.where(t)[1].mean(), np.where(t)[0].mean()] for t in pads[1:]]).mean(axis=0)
    heading = np.degrees(np.arctan2(-(toes[1] - py.mean()), toes[0] - px_.mean()))  # palm -> toes, y up
    out = []
    src = stamp.astype(np.float32)
    ang = step_deg
    while ang < 360 - 1e-6:
        tx, ty = art.to_px(radius * np.cos(np.radians(90 + ang)), radius * np.sin(np.radians(90 + ang)))
        turn = (90 + ang) - heading  # counter-clockwise as seen, which is +angle for cv2 on an image
        m = cv2.getRotationMatrix2D((float(sx), float(sy)), turn, scale)
        m[:, 2] += (tx - sx, ty - sy)
        out.append(cv2.warpAffine(src, m, (stamp.shape[1], stamp.shape[0]), flags=cv2.INTER_LINEAR) > 0.5)
        ang += step_deg
    return out


def _spread_pads(prints: np.ndarray, gap: float, px: float) -> np.ndarray:
    """A paw print's pads sit a hair apart in the art; each pad backs off from its neighbours until `gap` of
    orange fits between them (only the facing edges move)."""
    pads = V.components(V.opened(prints, 0.1 * px), int(0.1 * px * px))
    out = np.zeros_like(prints)
    d = (gap + 0.15) / 2 * px
    for c in pads:
        others = np.zeros_like(prints)
        for o in pads:
            if o is not c:
                others |= o
        out |= c & ~V.dilated(others, d)
    return V.closed(V.opened(out, 0.08 * px), 0.08 * px)


def _minus(g, *higher, sliver: float = 0.02):
    """g minus every higher-priority region, without the hairline slivers a near-coincident boundary leaves."""
    out = g.difference(unary_union(list(higher))) if higher else g
    out = out.buffer(-0.01, join_style="mitre").buffer(0.01, join_style="mitre")
    return V.multi(unary_union([q for q in V.multi(out).geoms if q.area >= sliver]))


def _tile(regions: list, outline, reach: float, dust: float = 0.02) -> list:
    """Disjoint regions, in priority order, grown into the gaps between them so that together they tile `outline`:
    each takes what's left of the gaps within `reach` of it (bits that only meet it at a corner are dropped as dust)."""
    gaps = outline.difference(unary_union(regions))
    out = []
    for g in regions:
        take = gaps.intersection(g.buffer(reach))
        gaps = gaps.difference(take)
        grown = V.multi(unary_union([g, *V.multi(take).geoms]))
        out.append(V.multi(unary_union([q for q in grown.geoms if q.area >= dust])))
    return out


# ---- the design -----------------------------------------------------------------------------------------------

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

    # --- paw prints: the 12 o'clock print (upright) is the stamp; copies go evenly around the ring
    ring_zone = (D > art.r + p.circle_w + 0.3) & (D < art.R - p.circle_w - 0.3)
    _, _, kept_bg = I.split(bg_ink & ring_zone, px, p)
    stamp = np.zeros_like(ink)  # the print's pad and toes are separate marks: take them all, nothing bigger
    for c in V.components(V.opened(kept_bg, 0.08 * px), int(0.3 * px * px)):
        ys, xs = np.where(c)
        x, y = art.to_mm(xs.mean(), ys.mean())
        if abs(x) < 2.5 and y > 0 and (xs.max() - xs.min()) < 3 * px and (ys.max() - ys.min()) < 3 * px:
            stamp |= c
    prints = [_spread_pads(m, p.pad_gap, px)
              for m in _stamp_around(stamp, art, (art.r + art.R) / 2, p.paw_print_step, p.paw_print_scale)]

    # --- the figure: cat + ribbon fills and ink, moved down
    dy = int(round(p.figure_drop * px))
    cat_mask, ribbon_mask, fig_ink_s = (_shift(m, dy) for m in (cat, ribbon, fig_ink))
    cls_s = _shift(cls, dy)
    thick, thin, kept = I.split(fig_ink_s, px, p)
    ears = E.masks(p, art, cls.shape)  # the ears' drawn strokes replace the traced ones; no fill beyond their arches
    thick, thin = thick & ~ears.erase, (thin & ~ears.erase) | ears.ink
    cat_mask = cat_mask & ~ears.outside
    pink = cls_s == C["pink"]
    iris = cls_s == C["iris"]

    # nose, mouth and whiskers: drawn (muzzle.py). Everything traced in the muzzle zone goes (the tooth too), and
    # the traced whiskers along the drawn ones, short of the face's outline; the pink tongue turns white
    muzzle = MZ.shapes(p)
    face_edge = V.dilated(~V.closed(cat_mask | fig_ink_s, 0.1 * px), 0.6 * px)
    muzzle_box = E.raster(muzzle.zone, art, cls.shape)
    muzzle_erase = muzzle_box | (E.raster(muzzle.erase, art, cls.shape) & ~face_edge)
    muzzle_ink = E.raster(muzzle.ink, art, cls.shape)
    thick, thin = thick & ~muzzle_erase, (thin & ~muzzle_erase) | muzzle_ink
    nose = E.raster(muzzle.nose, art, cls.shape)

    # eyes: drawn (eyes.py) in place of the traced ones; brown in the face band under them, their colors on top
    eye_shapes = EY.shapes(p)
    eye_mask = E.raster(unary_union([e.outer for e in eye_shapes]), art, cls.shape)
    eye_zone = E.raster(unary_union([e.outer.buffer(p.eye_erase) for e in eye_shapes]), art, cls.shape)
    thick, thin = thick & ~eye_zone, thin & ~eye_zone
    # paws: drawn (paws.py); traced ink inside them goes, the face band under them is white
    paw_shapes = PW.shapes(p)
    paw_mask = E.raster(unary_union([w.outer for w in paw_shapes]), art, cls.shape)
    above = []  # the band over each paw's top is plain white fur up to the rim (no traced arm line or shading)
    for w in paw_shapes:
        x0, y0, x1, y1 = w.outer.bounds
        inset = 0.15 * (x1 - x0)  # the corners, where the body's outline meets the paw, keep their lines
        above.append(w.outer.buffer(p.paw_top_clear).difference(w.outer).intersection(
            box(x0 + inset, y1 - p.paw_top_depth, x1 - inset, y1 + 1)))
    paw_top = E.raster(unary_union(above), art, cls.shape)
    thick, thin = thick & ~paw_mask & ~paw_top, thin & ~paw_mask & ~paw_top
    eyes = [(e.outer.centroid.x, e.outer.centroid.y, float(np.sqrt(e.outer.area / np.pi))) for e in eye_shapes]

    # the ribbon's folds ended at the ring before the drop; sweep them down so they still touch it
    under_ring = _sweep_down(D <= art.R, dy) & (D > art.R)
    outside = ribbon & (D > art.R - 0.2)
    circle_ink = V.dilated(bg_ink & (np.abs(D - (art.R - p.circle_w / 2)) < p.circle_w / 2 + 0.2), 0.6 * px)
    fold = np.zeros_like(ribbon)
    for c in V.components(outside, int(1.0 * px * px)):  # a fold's yellow meets the ring's own outline; the band in
        if (c & circle_ink & (Y < 0)).any():  # front of the ring interrupts that outline, so its ends don't
            fold |= c
    fold_ink = ink & V.dilated(fold, 0.4 * px) & ~V.dilated(ribbon & ~fold, 0.4 * px)
    ext_ink = _sweep_down(fold_ink, dy) & under_ring
    ext_fill = _sweep_down(fold, dy) & under_ring & ~ext_ink
    ext_ink = V.dilated(V.opened(V.closed(ext_ink, 0.1 * px), (p.line_w - 0.1) / 2 * px), 0.05 * px)
    ribbon_mask = (ribbon_mask | ext_fill) & ~paw_mask

    white_src = np.isin(cls_s, [C[n] for n in ("cat_white", "cat_white2", "cat_tan", "cat_tan2", "cat_tan3",
                                                "pink_light")]) | (pink & ~nose)
    # round the drawn eyes, what was the traced eye's ink is face white (orange fur stays orange)
    orange_src = np.isin(cls_s, [C[n] for n in ("cat_orange", "cat_orange2", "ear")])
    cat_mask = cat_mask | (eye_zone & ~eye_mask) | (muzzle_box & ~nose) | paw_mask | paw_top
    white_src = white_src | ((eye_zone & ~eye_mask) | (muzzle_box & ~nose)) & ~orange_src | paw_mask | paw_top

    def labels(ink_print):
        """Face-band label map: ribbon / cat white / cat orange / ink, gap-free inside the figure."""
        cat_region = _big(V.closed(cat_mask | pink | iris | ink_print, 0.1 * px), p.cat_min_area * px * px)
        cat_fill = cat_region & ~ribbon_mask
        figure = np.zeros_like(pink)
        for c in V.components(V.closed(cat_fill | ribbon_mask | ink_print, 0.15 * px), int(p.cat_min_area * px * px)):
            figure |= ndi.binary_fill_holes(c)
        cat_white = V.opened(white_src & cat_fill, p.fill_min / 2 * px)
        cat_orange = V.opened(cat_fill & ~cat_white, p.fill_min / 2 * px)
        lab = np.zeros(cls.shape, np.uint8)
        lab[V.opened(ribbon_mask, p.fill_min / 2 * px)] = YELLOW
        lab[cat_orange] = ORANGE
        lab[cat_white] = WHITE
        lab[ink_print | nose | eye_mask] = BROWN
        lab = _drop_islands(_fill_nearest(lab, figure), figure, p.min_island * px * px)
        return lab, figure, cat_fill

    # whiskers: thin strokes beside the nose that aren't part of a thick mark, the head's outline or a paw
    nys, nxs = np.where(nose)
    nx, ny = art.to_mm(nxs.mean(), nys.mean())
    dx0, dx1, dy0, dy1 = p.whisker_zone
    if dx1 > dx0:  # an empty zone keeps every whisker
        zone = (np.abs(X - nx) >= dx0) & (np.abs(X - nx) <= dx1) & (Y - ny >= dy0) & (Y - ny <= dy1)
        outline = V.dilated(~V.closed(cat_mask | fig_ink_s, 0.1 * px), 0.6 * px)  # near the figure's edge
        thin &= ~(zone & ~V.dilated(thick, 0.35 * px) & ~outline & ~V.dilated(paw_mask, 0.8 * px))
    ink_print = thick | thin | ext_ink

    # pass 2: the label map that prints
    lab, figure, cat_fill = labels(ink_print)
    fig_top = float(art.to_mm(0, np.where(figure)[0].min())[1])
    paws, paw_ink = paw_mask, np.zeros_like(paw_mask)  # the paws join the top band as vectors

    # letters: marks surrounded by ribbon yellow (the outline isn't; the cat's marks aren't), each smoothed
    letters = np.zeros_like(pink)
    near = V.dilated(ribbon_mask, 2.0 * px)
    r_s = p.letter_smooth * px
    for c in V.components(V.opened(kept, 0.1 * px), int(0.5 * px * px)):
        if (c & ~near).any() or (c & cat_fill).any():
            continue
        rim = V.dilated(c, 0.35 * px) & ~c
        if (rim & ribbon_mask).sum() >= p.letter_surround * rim.sum():
            g = V.closed(V.opened(c, r_s), r_s)
            letters |= cv2.GaussianBlur(g.astype(np.float32), (0, 0), 0.6 * r_s) > 0.5

    # top band rests on the face band: under letters the face band is yellow, under paw lines white.
    # Splitting a line between bands leaves slivers; marks thinner than a line join the nearest fill.
    r_line = (p.line_w - 0.05) / 2 * px
    paw_ink = V.opened(paw_ink, r_line)
    letters = V.opened(letters, r_line)
    letters = _open_counters(letters, cls_s == C["ribbon"], p.counter_min_d * px)
    glyph_zone = V.dilated(ndi.binary_fill_holes(letters), 0.3 * px)
    letters &= ~V.dilated((lab == BROWN) & ~glyph_zone, p.letter_clear * px)  # a letter never touches the ribbon's outline
    top_brown = letters | paw_ink  # the eyes and nose join as vectors
    top_brown = _big(top_brown, p.min_island * px * px)
    top_white = np.zeros_like(paw_mask)  # paws, eyes: vectors
    face = lab.copy()
    face_brown = V.opened((lab == BROWN) & ~glyph_zone & ~paw_ink, r_line) | eye_mask | nose  # yellow under a glyph
    face[(lab == BROWN) & ~face_brown] = EMPTY
    face[paw_mask] = EMPTY  # what's round a paw is filled from outside it, not from the paw's own white
    face = _drop_islands(_fill_nearest(face, figure), figure, p.min_island * px * px)
    face[paw_mask] = EMPTY
    for k in (YELLOW, WHITE, ORANGE):  # fill slivers thinner than a nozzle join their neighbours
        face[(face == k) & ~V.opened(face == k, p.sliver / 2 * px)] = EMPTY
    face = _drop_islands(_fill_nearest(face, figure & ~paw_mask), figure & ~paw_mask, p.min_island * px * px)
    face[paw_mask] = WHITE
    face_ink = face == BROWN

    # --- ring ink: the circles and paw prints run on under the figure's edge (and the outer circle past the ring);
    # the vectors below cut them exactly where the figure and the silhouette end
    hole_r = p.hole_d / 2
    hole = (0.0, art.R - p.hole_wall - hole_r, hole_r)
    outer_circle = (D > art.R - p.circle_w) & (D <= art.R + 0.1)
    disc_circle = (D > art.r) & (D <= art.r + p.circle_w)
    paws_ring = np.zeros_like(ink)
    ribbon_zone = V.dilated(ribbon_mask | (ink_print & ~V.dilated(cat_fill, 0.3 * px)), 0.8 * px)
    for m in prints:  # a print the ribbon would cut is left out altogether (an ear tip over one is the logo's look)
        if not (m & ribbon_zone).any():
            paws_ring |= m
    ring_ink = (outer_circle | disc_circle | paws_ring) & ~V.eroded(figure, 0.1 * px)

    def poly(m):
        return V.mask_polys(m, art.to_mm, px, p.vec_smooth, p.vec_tol) if m.any() else MultiPolygon()

    # vectorize. Every edge seen from above is shared exactly by the colors on either side: neighbouring contours,
    # traced on their own, differ by up to vec_tol, and a gap shows the band below as a thin line between two
    # colors. In the face band higher priority wins the overlaps and the gaps go to a neighbour; the ring ink, the
    # silhouette and the base band are cut by the figure's own outline.
    face_g = [poly(face_ink)]
    for k in (WHITE, ORANGE, YELLOW):
        face_g.append(_minus(poly(face == k), *face_g))
    figure_g = V.multi(unary_union(face_g).buffer(p.seam).buffer(-p.seam))
    face_ink_g, cat_w_g, cat_o_g, ribbon_g = _tile(face_g, figure_g, p.seam)
    # under each eye the face band is the eye's own outline, not its traced copy: their edges coincide
    eye_all = unary_union([*(e.outer for e in eye_shapes), muzzle.nose])  # drawn shapes raised in the top band
    clear = 3 * p.seam  # the traced leftovers round a drawn eye or nose go to the fills beside it
    strokes_g = muzzle.ink  # the muzzle's strokes, exactly
    traced = unary_union([eye_all.buffer(clear), muzzle.zone.intersection(strokes_g.buffer(clear))])
    paw_all = unary_union([w.outer for w in paw_shapes])
    face_ink_g = V.multi(unary_union([_minus(face_ink_g, traced), eye_all, strokes_g]).difference(paw_all))
    figure_g = V.multi(unary_union([figure_g, face_ink_g, paw_all]))
    # the paw's white goes under it exactly: the traced white round it is cleared and refilled from outside the paw
    cat_w_g, cat_o_g, ribbon_g = (g.difference(paw_all.buffer(clear)) for g in (cat_w_g, cat_o_g, ribbon_g))
    cat_w_g, cat_o_g, ribbon_g = _tile([_minus(g, face_ink_g) for g in (cat_w_g, cat_o_g, ribbon_g)],
                                       figure_g.difference(face_ink_g).difference(paw_all), clear + p.seam)
    paw_inner = unary_union([w.outer.buffer(-p.line_w) for w in paw_shapes])  # white under it, brown under its rim
    cat_w_g = V.multi(unary_union([cat_w_g, paw_inner]))
    face_ink_g = V.multi(unary_union([face_ink_g, paw_all.difference(paw_inner)]))
    face_ink_g, cat_w_g, cat_o_g, ribbon_g = _tile([face_ink_g, cat_w_g, cat_o_g, ribbon_g], figure_g,
                                                   3 * p.seam, dust=0)  # no gap left, however small
    # fill narrower than a nozzle between brown lines (wedges where lines meet, flecks) can't print cleanly: it goes
    # to the brown, and so does any fill piece too small to print (the white under a paw doesn't count: it's covered)
    fills = unary_union([cat_w_g.difference(paw_all), cat_o_g, ribbon_g]).buffer(0)
    narrow = [fills.difference(fills.buffer(-p.printer.nozzle / 2).buffer(p.printer.nozzle / 2))]
    kept = []
    for g in (cat_w_g, cat_o_g, ribbon_g):
        g = V.multi(g.difference(narrow[0]))
        narrow += [q for q in g.geoms if q.area < p.min_island]
        kept.append(V.multi(unary_union([q for q in g.geoms if q.area >= p.min_island])))
    cat_w_g, cat_o_g, ribbon_g = kept
    face_ink_g = V.multi(unary_union([face_ink_g, *narrow]).difference(unary_union(kept)))  # never over a fill
    silhouette_g = V.multi(unary_union([Point(0, 0).buffer(art.R, quad_segs=256), figure_g]))
    ring_ink_g = _minus(poly(ring_ink).intersection(silhouette_g), figure_g)
    raised = unary_union([eye_all, paw_all])
    top_brown_g = V.multi(unary_union([_minus(poly(top_brown), raised), *(e.brown for e in eye_shapes), muzzle.nose,
                                       *(w.brown for w in paw_shapes)]))
    top_white_g = V.multi(unary_union([*(e.white for e in eye_shapes), *(w.white for w in paw_shapes)]))
    # nothing seen from above may be a speck: backdrop boxed in between brown lines (a pocket smaller than an island,
    # a wedge narrower than base_sliver) fills with ring ink, and raised white narrower than a nozzle turns brown
    hx, hy, hr = hole  # the hole's brown ring sits on the orange base like a paw print
    ring_ink_g = V.multi(unary_union([ring_ink_g, Point(hx, hy).buffer(hr + p.hole_ring_w, 64)]))
    seen = silhouette_g.difference(unary_union([figure_g, ring_ink_g]))
    specks = [q for q in V.multi(seen).geoms if q.area < p.min_island]
    wedges = seen.difference(seen.buffer(-p.base_sliver / 2).buffer(p.base_sliver / 2))
    wedges = wedges.intersection(figure_g.buffer(0.5))  # against the cat; the ring prints' pad gaps stay open
    ring_ink_g = _minus(V.multi(unary_union([ring_ink_g, *specks, wedges])))  # _minus drops the dust
    thin_white = top_white_g.difference(top_white_g.buffer(-p.printer.nozzle / 2).buffer(p.printer.nozzle / 2))
    top_brown_g = _minus(V.multi(unary_union([top_brown_g, thin_white])))
    top_white_g = _minus(top_white_g, thin_white)
    # the base band's white/orange seam is never seen: it runs under the disc circle and tucked under the figure
    base_white_g = V.multi(unary_union([Point(0, 0).buffer(art.r + p.circle_w / 2, quad_segs=256),
                                        *(q for q in V.multi(figure_g.buffer(-p.base_tuck)).geoms
                                          if q.area >= p.min_island)]))
    base_orange_g = _minus(silhouette_g, base_white_g)
    d = Design(
        silhouette=silhouette_g, hole=hole,
        base_white=base_white_g, base_orange=base_orange_g,
        ribbon=ribbon_g, cat_white=cat_w_g, cat_orange=cat_o_g,
        face_ink=face_ink_g, ring_ink=ring_ink_g,
        top_white=top_white_g, top_brown=top_brown_g, paws=V.multi(paw_all),
        eyes=eyes, figure_top=fig_top, R=art.R, r=art.r,
        masks=dict(ink=ink, fig_ink=fig_ink_s, thick=thick, thin=thin, figure=figure, face=face, lab=lab,
                   face_ink=face_ink, ring_ink=ring_ink, top_white=top_white, top_brown=top_brown,
                   letters=letters, paws=paws, paw_ink=paw_ink, nose=nose, eye_mask=eye_mask,
                   paws_ring=paws_ring),
    )
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
