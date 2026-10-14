"""The front design as 2D regions per print band, in mm, from the classified logo.

Raster work at the art's resolution, vectorized at the end. The figure (cat + ribbon + their ink) is moved down
by figure_drop; the ring, its circles and paw prints stay. Each band is a gap-free label map, so the regions of
one band tile it exactly and never overlap."""
import dataclasses
from dataclasses import dataclass, field
from functools import lru_cache

import cv2
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPolygon, Point
from shapely.ops import unary_union

from . import art as A
from . import ears as E
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


def _fit_circle(mask: np.ndarray, art: A.Art) -> tuple:
    ys, xs = np.where(mask)
    (cx, cy), r = cv2.minEnclosingCircle(np.column_stack([xs, ys]).astype(np.float32))
    x, y = art.to_mm(cx, cy)
    return float(x), float(y), float(r / art.px_mm)


def _disc(shape, art: A.Art, x: float, y: float, r: float) -> np.ndarray:
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    ex, ey = art.to_px(x, y)
    return (xx - ex) ** 2 + (yy - ey) ** 2 <= (r * art.px_mm) ** 2


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
    """Copies of an upright mark placed every step_deg around the ring at `radius`, each pointing outward, skipping
    12 o'clock (the hole). The copies are what print: the logo's prints sit at uneven radii."""
    ys, xs = np.where(stamp)
    sx, sy = xs.mean(), ys.mean()
    out = []
    src = stamp.astype(np.float32)
    ang = step_deg
    while ang < 360 - 1e-6:
        tx, ty = art.to_px(radius * np.cos(np.radians(90 + ang)), radius * np.sin(np.radians(90 + ang)))
        m = cv2.getRotationMatrix2D((float(sx), float(sy)), -ang, scale)  # image y points down: clockwise = +angle
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

    # pink: the nose is the top pink blob; the tongue and anything else turn white, their outline goes too
    nose, best = np.zeros_like(pink), None
    for c in V.components(pink, int(0.3 * px * px)):
        y = art.to_mm(0, np.where(c)[0].mean())[1]
        if best is None or y > best:
            best, nose = y, c
    nose = V.closed(nose | (V.dilated(nose, 0.15 * px) & thick), 0.1 * px)

    # eyes: round dark/iris blobs inside the cat, the two largest; one glint each (the biggest white spot)
    eye_src = V.opened((cls_s == C["ink"]) | iris, 0.3 * px) & V.eroded(cat_mask | fig_ink_s, 0.2 * px)
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
        for g in spots[:1]:
            gx, gy, gr = _fit_circle(g, art)
            glints |= _disc(cls.shape, art, gx, gy, min(max(gr, p.eye_glint_min_d / 2), 0.35 * r))

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
    ribbon_mask = ribbon_mask | ext_fill

    white_src = np.isin(cls_s, [C[n] for n in ("cat_white", "cat_white2", "cat_tan", "cat_tan2", "cat_tan3",
                                                "pink_light")]) | (pink & ~nose)

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

    def find_paws(lab):
        """The big white blobs at the ribbon. Closing the ink shuts the wrist gap that joins a paw to the chest
        fur; the rim the closing ate is grown back from the white."""
        paws = np.zeros_like(pink)
        near_ribbon = V.dilated(ribbon_mask, 1.0 * px)
        white = lab == WHITE
        core = white & ~V.closed(lab == BROWN, p.paw_close / 2 * px)
        for c in V.components(core, int(p.paw_min_area * px * px)):
            if (c & near_ribbon).any() and c.sum() <= p.paw_max_area * px * px:  # the chest between them is bigger
                paws |= white & V.dilated(c, p.paw_close / 2 * px + 2) & ~V.dilated(lab == YELLOW, 0.05 * px)
        return paws

    # pass 1: find the paws with every stroke in place and untrimmed (the arm's top edge doubles as a whisker,
    # and the trimmed stroke ends would widen the wrist gap)
    _, thin_full, _ = I.split(fig_ink_s, px, dataclasses.replace(p, spur=0.0))
    thin_full = (thin_full & ~ears.erase) | ears.ink
    lab0, _, _ = labels(thick | thin_full | ext_ink)
    paws0 = find_paws(lab0)

    # whiskers: thin strokes beside the nose that aren't part of a thick mark, the head's outline or a paw
    nys, nxs = np.where(nose)
    nx, ny = art.to_mm(nxs.mean(), nys.mean())
    dx0, dx1, dy0, dy1 = p.whisker_zone
    if dx1 > dx0:  # an empty zone keeps every whisker
        zone = (np.abs(X - nx) >= dx0) & (np.abs(X - nx) <= dx1) & (Y - ny >= dy0) & (Y - ny <= dy1)
        outline = V.dilated(~V.closed(cat_mask | fig_ink_s, 0.1 * px), 0.6 * px)  # near the figure's edge
        thin &= ~(zone & ~V.dilated(thick, 0.35 * px) & ~outline & ~V.dilated(paws0, 0.8 * px))
    ink_print = thick | thin | ext_ink

    # pass 2: the label map that prints
    lab, figure, cat_fill = labels(ink_print)
    fig_top = float(art.to_mm(0, np.where(figure)[0].min())[1])
    paws = paws0 & (lab == WHITE)  # found with the untrimmed strokes: trimmed ends widen the wrist gap
    paw_ink = (lab == BROWN) & V.dilated(paws, 0.4 * px) & ~eye_mask

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
    top_brown = (eye_mask & ~glints) | nose | letters | paw_ink
    top_brown = _big(top_brown, p.min_island * px * px)
    top_white = (paws & ~paw_ink) | glints
    face = lab.copy()
    face_brown = V.opened((lab == BROWN) & ~glyph_zone & ~paw_ink, r_line) | eye_mask | nose  # yellow under a glyph
    face[(lab == BROWN) & ~face_brown] = EMPTY
    face = _drop_islands(_fill_nearest(face, figure), figure, p.min_island * px * px)
    for k in (YELLOW, WHITE, ORANGE):  # fill slivers thinner than a nozzle join their neighbours
        face[(face == k) & ~V.opened(face == k, p.sliver / 2 * px)] = EMPTY
    face = _drop_islands(_fill_nearest(face, figure), figure, p.min_island * px * px)
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
    silhouette_g = V.multi(unary_union([Point(0, 0).buffer(art.R, quad_segs=256), figure_g]))
    ring_ink_g = _minus(poly(ring_ink).intersection(silhouette_g), figure_g)
    top_brown_g = poly(top_brown)
    top_white_g = _minus(poly(top_white), top_brown_g)
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
        top_white=top_white_g, top_brown=top_brown_g, paws=poly(paws | paw_ink),
        eyes=eyes, figure_top=fig_top, R=art.R, r=art.r,
        masks=dict(ink=ink, fig_ink=fig_ink_s, thick=thick, thin=thin, figure=figure, face=face, lab=lab,
                   face_ink=face_ink, ring_ink=ring_ink, top_white=top_white, top_brown=top_brown,
                   letters=letters, paws=paws, paw_ink=paw_ink, nose=nose, eye_mask=eye_mask, glints=glints,
                   paws_ring=paws_ring),
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
