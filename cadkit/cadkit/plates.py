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
         colors: int | None = None, keepout=_SLICER) -> list[list[tuple[str, Shape]]]:
    """Pack (name, flat shape) items onto as few beds as possible; multi-color parts get their own plates unless
    the printer has one color. printer and colors default to your settings.

    keepout: (x0, y0, x1, y1) on the bed that multi-color plates leave free for the slicer's prime tower; by default
    the active slicer's (cadkit.slicers.active().tower_keepout()), None for none."""
    from cadkit.settings import settings
    printer = printer or default()
    colors = settings().colors if colors is None else colors
    if colors == 1:
        return _pack(items, printer, gap)
    if keepout is _SLICER:
        from cadkit import slicers
        keepout = slicers.active().tower_keepout()
    two = [it for it in items if is_multi_color(it[1])]
    one = [it for it in items if not is_multi_color(it[1])]
    return (_pack(two, printer, gap, keepout) if two else []) + (_pack(one, printer, gap) if one else [])


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
