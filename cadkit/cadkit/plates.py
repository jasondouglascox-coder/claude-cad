"""Pack flat parts onto build plates.

MaxRects (best-short-side-fit): every item is inflated by GAP, both rotations are tried, and free rectangles are
split and pruned. Multi-color parts never share a plate with single-color parts, so a single-color plate needs no
swaps (AMS swaps are slow); on a one-color printer (settings colors = 1) everything packs together. Nest awkward pairs yourself first (e.g. two
long panels head to tail) and pass the pair as one Compound: compounds stay together.
"""
from dataclasses import dataclass, field

from build123d import Compound, Pos, Rot, Shape

from cadkit.printer import Printer, default

GAP = 3.0  # mm between parts on a plate


@dataclass
class Plate:
    name: str
    qty: int  # how many times to print it
    items: list  # (part name, shape placed on the bed)
    color_changes: int | None = None  # swaps this plate's design accepts; None = the budget in settings
    blockers: list = field(default_factory=list)  # (part name, volume placed on the bed): no support inside it


@dataclass
class _Rect:
    x: float
    y: float
    w: float
    h: float


def zeroed(s: Shape) -> Shape:
    """Move a shape so its bounding box starts at the origin."""
    bb = s.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * s


def is_multi_color(s: Shape) -> bool:
    """A multi-color print part: a Compound of colored bodies stacked by height, lowest color first (e.g. brown ties
    under gray plates). Two bodies make one color change; three make two."""
    return isinstance(s, Compound) and len(s.children) >= 2 and all(c.color is not None for c in s.children)


is_two_color = is_multi_color  # the original name


def bodies(s: Compound) -> list[Shape]:
    """A multi-color part's bodies where the part is now. Moving or turning a Compound (a packer placing it) moves
    the Compound only: its children keep their first place, so apply the Compound's location to each."""
    return [s.location * c for c in s.children]


def _color(name: str, body: Shape):
    col = getattr(body, "color", None)
    return None if col is None else tuple(round(c, 3) for c in tuple(col)[:3])


def _bands(x, key=None) -> list[tuple[float, float, object]]:
    """(bottom, top, key) of every color body in a shape or a plate's [(name, shape)]. key(name, body) says which
    filament a body prints in; by default its color (a part's name for a whole part, a body's label in a
    multi-color part)."""
    key = key or _color
    items = x if isinstance(x, list) else [(getattr(x, "label", ""), x)]
    out = []
    for name, s in items:
        for label, b in ([(c.label, c) for c in bodies(s)] if is_multi_color(s) else [(name, s)]):
            bb = b.bounding_box()
            out.append((bb.min.Z, bb.max.Z, key(label, b)))
    return out


def colors_used(x, key=None) -> int:
    """Distinct colors (or filaments, with key) in a shape or a plate's [(name, shape)]."""
    return len({c for _, _, c in _bands(x, key)})


def color_changes(x, printer: Printer | None = None, key=None) -> int:
    """Filament swaps to print a shape or a plate's [(name, shape)], layer by layer: k colors in a layer cost k - 1
    swaps, plus one when the layer can't start with the color the last one ended on. Stacked colors (brown up to the
    seam, gray above) cost one swap per seam; colors side by side in the same layers cost a swap every layer.
    key(name, body) -> filament counts filaments instead of colors (two colors on one filament are one)."""
    printer = printer or default()
    bands = _bands(x, key)
    top = max(hi for _, hi, _ in bands)
    zs = [printer.first / 2]  # the middle of each layer
    while (z := printer.first + printer.layer * (len(zs) - 0.5)) < top:
        zs.append(z)
    layers = [{c for lo, hi, c in bands if lo < z < hi} for z in zs]
    layers = [l for l in layers if l]
    best = {None: 0}  # filament the last layer ended on -> fewest swaps so far
    for here in layers:
        nxt = {}
        for last, cost in best.items():
            for end in here:
                if len(here) == 1:
                    c = cost + (last is not None and last != end)
                elif last in here:
                    if end == last:
                        continue  # started on it, so ends on another
                    c = cost + len(here) - 1
                else:
                    c = cost + len(here) - (last is None)
                nxt[end] = min(nxt.get(end, c), c)
        best = nxt
    return min(best.values())


def _free_after(free: list[_Rect], u: _Rect) -> list[_Rect]:
    out = []
    for r in free:
        if u.x >= r.x + r.w or u.x + u.w <= r.x or u.y >= r.y + r.h or u.y + u.h <= r.y:
            out.append(r)
            continue
        if u.x > r.x:
            out.append(_Rect(r.x, r.y, u.x - r.x, r.h))
        if u.x + u.w < r.x + r.w:
            out.append(_Rect(u.x + u.w, r.y, r.x + r.w - u.x - u.w, r.h))
        if u.y > r.y:
            out.append(_Rect(r.x, r.y, r.w, u.y - r.y))
        if u.y + u.h < r.y + r.h:
            out.append(_Rect(r.x, u.y + u.h, r.w, r.y + r.h - u.y - u.h))
    inside = lambda a, b: a.x >= b.x and a.y >= b.y and a.x + a.w <= b.x + b.w and a.y + a.h <= b.y + b.h
    return [a for i, a in enumerate(out) if not any(j != i and inside(a, b) for j, b in enumerate(out))]


_SLICER = object()  # pack(keepout=...) default: ask the active slicer


def pack(items: list[tuple[str, Shape]], printer: Printer | None = None, gap: float = GAP,
         colors: int | None = None, keepout=_SLICER, fill_gaps: bool = False) -> list[list[tuple[str, Shape]]]:
    """Pack (name, flat shape) items onto as few beds as possible; multi-color parts get their own plates unless
    the printer has one color. printer and colors default to your settings.

    keepout: (x0, y0, x1, y1) on the bed that multi-color plates leave free for the slicer's prime tower; by default
    the active slicer's (cadkit.slicers.active().tower_keepout()), None for none.

    fill_gaps: after packing by bounding rectangles, move parts from later plates into the open space around the
    real outlines on earlier ones (an L's empty corner, the inside of a frame), dropping plates that empty."""
    from cadkit.settings import settings
    printer = printer or default()
    colors = settings().colors if colors is None else colors
    run = (lambda its, ko=None: _fill(_pack(its, printer, gap, ko), printer, gap, ko)) if fill_gaps else \
        (lambda its, ko=None: _pack(its, printer, gap, ko))
    if colors == 1:
        return run(items)
    if keepout is _SLICER:
        from cadkit import slicers
        keepout = slicers.active().tower_keepout()
    two = [it for it in items if is_multi_color(it[1])]
    one = [it for it in items if not is_multi_color(it[1])]
    return (run(two, keepout) if two else []) + (run(one) if one else [])


RES = 0.5  # mm per cell of the footprint grid that fill_gaps searches


def _footprint(s: Shape, res: float = RES):
    """Boolean grid (rows = y, cols = x) of the shape's XY shadow from its bounding box's min corner: every face that
    isn't vertical, tessellated and filled (top and bottom faces together cover the shadow, either winding)."""
    import numpy as np
    bb = s.bounding_box()
    ox, oy = bb.min.X, bb.min.Y
    w, h = int(np.ceil(bb.size.X / res)) + 1, int(np.ceil(bb.size.Y / res)) + 1
    m = np.zeros((h, w), bool)
    for f in s.faces():
        try:
            if abs(f.normal_at(f.center()).Z) < 1e-3:
                continue
        except Exception:
            pass
        verts, tris = f.tessellate(0.2, 0.5)
        if not tris:
            continue
        pts = np.array([((v.X - ox) / res, (v.Y - oy) / res) for v in verts])
        for t in tris:
            (x0, y0), (x1, y1), (x2, y2) = pts[list(t)]
            d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(d) < 1e-12:
                continue
            c0, c1 = max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, w)
            r0, r1 = max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, h)
            gx, gy = np.meshgrid(np.arange(c0, c1) + 0.5, np.arange(r0, r1) + 0.5)
            a = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / d
            b = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / d
            m[r0:r1, c0:c1] |= (a >= -1e-6) & (b >= -1e-6) & (a + b <= 1 + 1e-6)
            for x, y in ((x0, y0), (x1, y1), (x2, y2)):  # slivers thinner than a cell still mark their corners
                m[min(int(y), h - 1), min(int(x), w - 1)] = True
    return m


def _grow(m, r: int):
    """Dilate a boolean grid by r cells (square)."""
    import numpy as np
    out = np.zeros((m.shape[0] + 2 * r, m.shape[1] + 2 * r), bool)
    for dy in range(2 * r + 1):
        for dx in range(2 * r + 1):
            out[dy:dy + m.shape[0], dx:dx + m.shape[1]] |= m
    return out


def _spot(occ, item, r: int):
    """Lowest, then leftmost (row, col) where the item's core fits inside occ's bed and its r-cell halo touches
    nothing; None if nowhere."""
    import numpy as np
    H, W = occ.shape
    h, w = item.shape
    if h > H or w > W:
        return None
    halo = _grow(item, r).astype(float)
    pad = np.zeros((H + 2 * r, W + 2 * r))
    pad[r:r + H, r:r + W] = occ
    shape = (pad.shape[0] + halo.shape[0], pad.shape[1] + halo.shape[1])
    corr = np.fft.irfft2(np.fft.rfft2(pad, shape) * np.conj(np.fft.rfft2(halo, shape)), shape)
    ok = corr[:H - h + 1, :W - w + 1] < 0.5
    hits = np.argwhere(ok)
    return None if not len(hits) else tuple(hits[0])


def _fill(plates_out: list, printer: Printer, gap: float, keepout=None) -> list:
    """Move parts from later plates into gaps on earlier ones, by their real footprints (fill_gaps)."""
    import numpy as np
    if len(plates_out) < 2:
        return plates_out
    off, res = printer.margin / 2, RES
    H, W = int(printer.usable_y / res), int(printer.usable_x / res)
    r = int(np.ceil(gap / res))

    def occupancy(pl):
        o = np.zeros((H, W), bool)
        if keepout is not None:
            x0, y0, x1, y1 = keepout
            o[max(int((y0 - off) / res), 0):max(int(np.ceil((y1 - off) / res)), 0),
              max(int((x0 - off) / res), 0):max(int(np.ceil((x1 - off) / res)), 0)] = True
        for _, s in pl:
            stamp(o, s)
        return o

    def stamp(o, s):
        bb = s.bounding_box()
        m = _footprint(s)
        i, j = int(round((bb.min.Y - off) / res)), int(round((bb.min.X - off) / res))
        i0, j0 = max(i, 0), max(j, 0)
        hh, ww = min(m.shape[0] - (i0 - i), H - i0), min(m.shape[1] - (j0 - j), W - j0)
        if hh > 0 and ww > 0:
            o[i0:i0 + hh, j0:j0 + ww] |= m[i0 - i:i0 - i + hh, j0 - j:j0 - j + ww]

    occ = [occupancy(pl) for pl in plates_out]
    for k in range(len(plates_out) - 1, 0, -1):
        for name, s in sorted(plates_out[k], key=lambda it: -_footprint(it[1]).sum()):
            done = False
            for t in range(k):
                for turn in (0, 90, 180, 270):
                    cand = zeroed(Rot(0, 0, turn) * zeroed(s)) if turn else zeroed(s)
                    m = _footprint(cand)
                    at = _spot(occ[t], m, r)
                    if at is None:
                        continue
                    placed = Pos(off + at[1] * res, off + at[0] * res, 0) * cand
                    plates_out[t].append((name, placed))
                    stamp(occ[t], placed)
                    plates_out[k] = [it for it in plates_out[k] if it[0] != name or it[1] is not s]
                    done = True
                    break
                if done:
                    break
    return [pl for pl in plates_out if pl]


def _pack(items: list[tuple[str, Shape]], printer: Printer, gap: float,
          keepout: tuple | None = None) -> list[list[tuple[str, Shape]]]:
    side_x, side_y = printer.usable_x + gap, printer.usable_y + gap  # every item carries the gap on its right/top
    off = printer.margin / 2
    start = [_Rect(0, 0, side_x, side_y)]
    if keepout is not None:  # bed coordinates -> packing coordinates; an item's gap stays on its own right/top
        x0, y0 = max(keepout[0] - off, 0.0), max(keepout[1] - off, 0.0)
        x1, y1 = min(keepout[2] - off, side_x), min(keepout[3] - off, side_y)
        if x1 > x0 and y1 > y0:
            start = _free_after(start, _Rect(x0, y0, x1 - x0, y1 - y0))
    todo = []
    for name, s in items:
        s = zeroed(s)
        bb = s.bounding_box()
        todo.append((name, s, bb.size.X + gap, bb.size.Y + gap))
    todo.sort(key=lambda t: (-max(t[2], t[3]), -t[2] * t[3]))
    plates_out = []
    while todo:
        free, placed, left = list(start), [], []
        for name, s, w, h in todo:
            best = None
            for r in free:
                for ww, hh, rot in ((w, h, False), (h, w, True)):
                    if ww <= r.w + 1e-9 and hh <= r.h + 1e-9:
                        key = (min(r.w - ww, r.h - hh), max(r.w - ww, r.h - hh))
                        if best is None or key < best[0]:
                            best = (key, r.x, r.y, ww, hh, rot)
            if best is None:
                left.append((name, s, w, h))
                continue
            _, x, y, ww, hh, rot = best
            shape = zeroed(Rot(0, 0, 90) * s) if rot else s
            placed.append((name, Pos(x + off, y + off, 0) * shape))
            free = _free_after(free, _Rect(x, y, ww, hh))
        if not placed:
            raise ValueError(f"{left[0][0]} does not fit on the bed")
        plates_out.append(placed)
        todo = left
    return plates_out
