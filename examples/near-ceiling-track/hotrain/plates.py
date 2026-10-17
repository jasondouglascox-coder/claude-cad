"""Build-plate kits: each bay prints as two half-span plates, plus one plate for the run ends.

Parts are packed with cadkit's MaxRects packer; two arch halves are nested head-to-tail first, since that is
what lets a half span fit on one A1 plate.
"""
from functools import lru_cache

from build123d import Compound, Pos, Rot, Shape

from cadkit import plates as cadkit_plates
from cadkit.plates import GAP, Plate, is_two_color
from cadkit.plates import zeroed as _zeroed

from hotrain import layout as L
from hotrain.params import P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, handrail, keystone, tie_ladder

@lru_cache(maxsize=None)
def nested_arch_pair(p: Params, bay_len: float) -> Compound:
    """A panel's two halves on one plate as close as GAP allows: the end half and the start half (the deck truss's
    mirror image; the arch's same half), the second head-to-tail or upright, whichever packs tighter."""
    tag = f"arch_half_{bay_len:.1f}mm"
    a = _zeroed(arch_half.make(p, bay_len))
    a.label = tag
    b = _zeroed(arch_half.make(p, bay_len, start=True))
    b.label = tag + ("_start" if arch_half.mirrored(p) else "")
    best = None
    for low in (_zeroed(Rot(0, 0, 180) * b), b):
        h = a.bounding_box().size.Y
        lo, hi = 0.0, h + GAP + 1
        for _ in range(14):  # binary search the smallest lift that keeps GAP clearance
            mid = (lo + hi) / 2
            if (Pos(0, mid, 0) * a).distance_to(low) >= GAP:
                hi = mid
            else:
                lo = mid
        if best is None or hi < best[0]:
            best = (hi, low)
    hi, low = best
    up = Pos(0, hi, 0) * a
    up.label, low.label = a.label, b.label
    return Compound(children=[low, up])


def pack(p: Params, items: list[tuple[str, Shape]]) -> list[list[tuple[str, Shape]]]:
    """cadkit's MaxRects packer on this project's printer (two-color parts get their own plates)."""
    return cadkit_plates.pack(items, p.printer)


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
    pooled onto shared "ladders" plates, one color change each; the per-bay kits are single-color. A kit that
    overflows its plate sends the overflow to shared "extras" plates (one of each per kit instance)."""
    L.validate_bays(p, bays)
    seen: dict[tuple, list[Plate]] = {}
    variants: dict[str, int] = {}
    order: list[tuple] = []
    pool = []  # two-color parts of every kit instance, repeats included
    spill: dict[tuple, list] = {}  # a kit's overflow past its first plate: shared extras plates, per instance
    extras = []
    for role, key, items in _kits(p, bays, ends):
        pool += [it for it in items if is_two_color(it[1])]
        items = [it for it in items if not is_two_color(it[1])]
        if key in seen:
            for pl in seen[key]:
                pl.qty += 1
            extras += spill[key]
            continue
        variants[role] = variants.get(role, 0) + 1
        base = role if variants[role] == 1 else f"{role}{variants[role]}"
        packed = pack(p, items)
        spill[key] = [(name.split("#")[0], _zeroed(s)) for pl in packed[1:] for name, s in _flatten(pl)]
        extras += spill[key]
        seen[key] = [Plate(base, 1, _flatten(packed[0]))]
        order.append(key)
    ladders = [Plate(f"ladders_{n + 1}", 1, _flatten(pl)) for n, pl in enumerate(pack(p, pool))] if pool else []
    shared = [Plate(f"extras_{n + 1}", 1, _flatten(pl)) for n, pl in enumerate(pack(p, extras))] if extras else []
    return ladders + [pl for key in order for pl in seen[key]] + shared


def _flatten(pl: list) -> list:
    flat = []
    for name, s in pl:
        if name.endswith("#pair"):  # keep each half's own name (the deck truss's start half is the mirror image)
            flat += [(f"{c.label}#{k}", c) for k, c in enumerate(cadkit_plates.bodies(s), start=1)]  # where packed
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
    """Plates for the three inside corners (printed 3x), the bridge corner, and the rod-bending jig. The white PLA
    ceiling cleats get their own plate: PLA and PETG print at different temperatures, and white beside gray in the
    same layers would swap filament every layer."""
    from hotrain import corner_layout as CL
    from hotrain.parts import rod_jig
    out = []
    for corner, qty in ((CL.inside_corner(), 3), (CL.bridge_corner(), 1)):
        kit = corner_kit(p, corner)
        petg = [it for it in kit if not it[0].startswith("ceiling_anchor")]
        pla = [it for it in kit if it[0].startswith("ceiling_anchor")]
        packed = pack(p, petg)
        for n, pl in enumerate(packed):
            name = f"{corner.name}_corner" + (f"_{n + 1}" if len(packed) > 1 else "")
            out.append(Plate(name, qty, pl))
        cleats = pack(p, pla) if pla else []
        out += [Plate(f"{corner.name}_corner_cleats" + (f"_{n + 1}" if len(cleats) > 1 else ""), qty, pl)
                for n, pl in enumerate(cleats)]
    out.append(Plate("rod_jig", 1, pack(p, [("rod_jig", rod_jig.make(p))])[0]))
    return out


def wire_test_plates(p: Params = P) -> list[Plate]:
    """The wire-rail curve test: one piece to seat the wire, then the 5 pieces of a 90° corner to run a train.
    They print at the web's fine layers (build.cmd_wire_test writes those slicer settings)."""
    from hotrain.parts import wire_curve
    single = [Plate("wire_curve_single", 1, pack(p, [("wire_curve", wire_curve.make_colored(p))])[0])]
    corner = pack(p, [(f"wire_curve#{k}", wire_curve.make_colored(p)) for k in range(p.wire_test_pieces)])
    return single + [Plate("wire_curve_corner" + (f"_{n + 1}" if len(corner) > 1 else ""), 1, pl)
                     for n, pl in enumerate(corner)]
