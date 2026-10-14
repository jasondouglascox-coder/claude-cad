"""Build-plate kits: each bay prints as two half-span plates, plus one plate for the run ends.

Parts are packed with a MaxRects (best-short-side-fit) packer; two arch halves are nested
head-to-tail first, since that is what lets a half span fit on one A1 plate.
"""
from dataclasses import dataclass
from functools import lru_cache

from build123d import Compound, Part, Pos, Rot, Shape

from hotrain import layout as L
from hotrain.params import P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, handrail, keystone, tie_ladder

GAP = 3.0  # mm between parts on a plate


@dataclass
class Plate:
    name: str
    qty: int
    items: list  # (part name, shape placed on the bed)


@dataclass
class _Rect:
    x: float
    y: float
    w: float
    h: float


def _zeroed(s: Shape) -> Shape:
    bb = s.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * s


@lru_cache(maxsize=None)
def nested_arch_pair(p: Params, bay_len: float) -> Compound:
    """Two arch halves head-to-tail (one turned 180°), as close as GAP allows."""
    a = _zeroed(arch_half.make(p, bay_len))
    w, h = a.bounding_box().size.X, a.bounding_box().size.Y
    low = _zeroed(Rot(0, 0, 180) * a)
    lo, hi = 0.0, h + GAP + 1
    for _ in range(14):  # binary search the smallest lift that keeps GAP clearance
        mid = (lo + hi) / 2
        if (Pos(0, mid, 0) * a).distance_to(low) >= GAP:
            hi = mid
        else:
            lo = mid
    return Compound(children=[low, Pos(0, hi, 0) * a])


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


def is_two_color(s: Shape) -> bool:
    """A multi-color print part (wood + steel bodies), e.g. a tie ladder or corner deck."""
    return isinstance(s, Compound) and len(s.children) == 2 and all(c.color is not None for c in s.children)


def pack(p: Params, items: list[tuple[str, Shape]]) -> list[list[tuple[str, Shape]]]:
    """Pack (name, flat shape) items onto as few beds as possible. Two-color parts get their own plates, so
    every plate has at most one color change (and single-color plates none). Compounds stay together."""
    two = [it for it in items if is_two_color(it[1])]
    one = [it for it in items if not is_two_color(it[1])]
    if two and one:
        return _pack(p, two) + _pack(p, one)
    return _pack(p, items)


def _pack(p: Params, items: list[tuple[str, Shape]]) -> list[list[tuple[str, Shape]]]:
    side = p.bed - p.bed_margin + GAP  # every item carries GAP on its right/top edge
    off = p.bed_margin / 2
    todo = []
    for name, s in items:
        s = _zeroed(s)
        bb = s.bounding_box()
        todo.append((name, s, bb.size.X + GAP, bb.size.Y + GAP))
    todo.sort(key=lambda t: (-max(t[2], t[3]), -t[2] * t[3]))
    plates_out = []
    while todo:
        free, placed, left = [_Rect(0, 0, side, side)], [], []
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
            shape = _zeroed(Rot(0, 0, 90) * s) if rot else s
            placed.append((name, Pos(x + off, y + off, 0) * shape))
            free = _free_after(free, _Rect(x, y, ww, hh))
        if not placed:
            raise ValueError(f"{left[0][0]} does not fit on the bed")
        plates_out.append(placed)
        todo = left
    return plates_out


def _ladder_key(p: Params, bays: list[float], seg: L.Segment, ends: tuple) -> tuple:
    r = lambda v: round(v - seg.x_start, 2)
    return ("ladder", round(seg.x_end - seg.x_start, 2), seg.female_start, seg.male_end,
            tuple((r(t.x), t.long, t.lip, t.gap) for t in L.ties(p, bays, ends) if seg.x_start < t.x < seg.x_end),
            tuple(r(x) for x in L.tab_xs(p, bays) if seg.x_start < x < seg.x_end),
            tuple((r(a), r(b)) for a, b in L.rod_tail_spans(p, bays, ends) if b > seg.x_start and a < seg.x_end))


def _rail_key(pc: L.HandrailPiece) -> tuple:
    return ("rail", round(pc.x_end - pc.x_start, 2), tuple(round(x - pc.x_start, 2) for x in pc.posts))


def _kits(p: Params, bays: list[float], ends: tuple) -> list[tuple[str, tuple, list]]:
    """(role, dedupe key, [(part name, shape-or-compound)]) per kit, in run order."""
    segs, rails = L.segments(p, bays, ends), L.handrail_pieces(p, bays, ends)
    rails_in = lambda s: [(k, pc) for k, pc in enumerate(rails) if s.x_start <= (pc.x_start + pc.x_end) / 2 < s.x_end]

    def deck(k: int) -> tuple[list, list]:
        s = segs[k]
        items = [(f"ladder_{k:02d}", tie_ladder.make_colored(p, bays, s, ends))]  # wood + steel bodies
        keys = [_ladder_key(p, bays, s, ends)]
        for j, pc in rails_in(s):
            items.append((f"handrail_{j:02d}", handrail.make(p, pc)))
            keys.append(_rail_key(pc))
        return items, keys

    kits = []
    for i, b in enumerate(bays):
        tag = f"{b:.1f}mm"
        half = [(f"arch_half_{tag}#pair", nested_arch_pair(p, b)), (f"keystone", keystone.make(p))]
        half += [(f"cross_frame_{tag}_{k}", cross_frame.make(p, L.cf_depth(p, b, u)))
                 for k, u in enumerate(L.post_us(p, b))]
        last_corner = i == len(bays) - 1 and ends[1] == L.CORNER  # the corner's anchor replaces this bracket
        b_extra = [] if last_corner else [("bracket", bracket.make(p))]
        for role, k, extra in (("A", 2 * i + 1, []), ("B", 2 * i + 2, b_extra)):
            d_items, d_keys = deck(k)
            key = (role, tag, tuple(d_keys))
            kits.append((f"bay_{tag}_{role}", key, half + extra + d_items))
    d_items, d_keys = deck(0)
    n_piers = 2 * sum(e == L.FREE for e in ends)
    first = [] if ends[0] == L.CORNER else [("bracket", bracket.make(p))]
    kit = [("end_pier", end_pier.make(p)) for _ in range(n_piers)] + first + d_items
    kits.append(("run_ends", ("E", ends, tuple(d_keys)), kit))
    return kits


def plates(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> list[Plate]:
    """Distinct plates with how many of each to print. Item names match out/manifest.csv
    (a nested arch pair counts as two arch halves). Two-color parts (tie ladders) from the whole run are
    pooled onto shared "ladders" plates, one color change each; the per-bay kits are single-color."""
    L.validate_bays(p, bays)
    seen: dict[tuple, list[Plate]] = {}
    variants: dict[str, int] = {}
    order: list[tuple] = []
    pool = []  # two-color parts of every kit instance, repeats included
    for role, key, items in _kits(p, bays, ends):
        pool += [it for it in items if is_two_color(it[1])]
        items = [it for it in items if not is_two_color(it[1])]
        if key in seen:
            for pl in seen[key]:
                pl.qty += 1
            continue
        variants[role] = variants.get(role, 0) + 1
        base = role if variants[role] == 1 else f"{role}{variants[role]}"
        packed = pack(p, items)
        seen[key] = [Plate(base if len(packed) == 1 else f"{base}_{n + 1}", 1, _flatten(pl))
                     for n, pl in enumerate(packed)]
        order.append(key)
    ladders = [Plate(f"ladders_{n + 1}", 1, _flatten(pl)) for n, pl in enumerate(pack(p, pool))] if pool else []
    return ladders + [pl for key in order for pl in seen[key]]


def _flatten(pl: list) -> list:
    flat = []
    for name, s in pl:
        if name.endswith("#pair"):
            flat += [(name.replace("#pair", "#1"), s.solids()[0]), (name.replace("#pair", "#2"), s.solids()[1])]
        else:
            flat.append((name, s))
    return flat


def all_in_one(p: Params, bays: list[float], ends: tuple = L.RUN_ENDS, name: str = "starter") -> list[Plate]:
    """Every part of a short run packed together on as few plates as possible (no per-bay kits), e.g. a
    single test bay."""
    items = [it for _, _, kit in _kits(p, bays, ends) for it in kit]
    return [Plate(f"{name}_{n + 1}", 1, _flatten(pl)) for n, pl in enumerate(pack(p, items))]


def corner_kit(p: Params, corner) -> list[tuple[str, Shape]]:
    """Every printed part of one corner, named like out/corners/*.step."""
    from hotrain import corner_assembly as CA
    from hotrain.parts import bow_deck, bow_frame, deep_bracket, floor_beam, rod_anchor
    from hotrain import corner_layout as CL
    items = []
    for sp in CL.spans(p, corner):
        kind = "curve" if sp.curved else "straight"
        items.append((f"corner_deck_{kind}", bow_deck.make_colored(p, sp.curved)))  # wood + steel bodies
        for k, _, _, ln in CA.frame_lines(p, sp.curved):
            items.append((f"corner_frame_{k}", bow_frame.make(p, ln)))
    from hotrain.parts import ceiling_anchor
    for i in range(1, len(CL.portals(p, corner)) - 1):
        items.append(("floor_beam", floor_beam.make(p)))
    items += [("ceiling_anchor", ceiling_anchor.make(p)) for _ in range(2 * len(corner.ceiling))]
    items += [("rod_anchor", rod_anchor.make(p)) for _ in range(2)]
    ps = CL.portals(p, corner)
    for i, wall in corner.deep:
        pt = ps[i]
        ang = pt.heading if wall == "A" else 90 - pt.heading
        items.append(("deep_bracket", deep_bracket.make(p, CL.wall_offset(p, corner, pt), ang)))
    return items


def corner_plates(p: Params = P) -> list[Plate]:
    """Plates for the three inside corners (printed 3x), the bridge corner, and the rod-bending jig."""
    from hotrain import corner_layout as CL
    from hotrain.parts import rod_jig
    out = []
    for corner, qty in ((CL.inside_corner(), 3), (CL.bridge_corner(), 1)):
        packed = pack(p, corner_kit(p, corner))
        for n, pl in enumerate(packed):
            name = f"{corner.name}_corner" + (f"_{n + 1}" if len(packed) > 1 else "")
            out.append(Plate(name, qty, pl))
    out.append(Plate("rod_jig", 1, pack(p, [("rod_jig", rod_jig.make(p))])[0]))
    return out
