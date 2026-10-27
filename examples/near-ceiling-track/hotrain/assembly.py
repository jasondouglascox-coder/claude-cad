"""Every part of a run placed where it goes, for Onshape review and interference checks."""
from dataclasses import replace

from build123d import Compound, Part

from cadkit.clash import find_clashes  # noqa: F401  (assembly.find_clashes for the tests and build check)

from hotrain import layout as L
from hotrain.params import P, Params
from hotrain.parts import arch_half, bracket, cross_frame, end_pier, handrail, keystone, tie_ladder


def named(part: Part, name: str) -> Part:
    """Label a base shape with its part type; this becomes the STEP product name Onshape shows."""
    part.label = name
    return part


def side(y: float) -> str:
    return "room" if y > 0 else "wall"


def placed_parts(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> list[tuple[str, Part]]:
    """ends: what each run end meets (layout.FREE / layout.CORNER). A corner end gets no bracket and no
    end piers (the corner's rod anchor takes the pier), and the deck stops at the anchor."""
    L.validate_bays(p, bays)
    out: list[tuple[str, Part]] = []
    xs = L.pier_xs(bays)
    key = named(keystone.make(p), "keystone")
    for i, (x0, b) in enumerate(zip(xs, bays)):
        half = named(arch_half.make(p, b), f"arch_half_{b:.1f}mm")
        first = named(arch_half.make(p, b, start=True), f"arch_half_{b:.1f}mm_start") if arch_half.mirrored(p) else half
        for y in p.rail_ys:
            out.append((f"bay{i}_{side(y)}_arch_start", arch_half.place_half(p, x0, b, y, start=True) * first))
            out.append((f"bay{i}_{side(y)}_arch_end", arch_half.place_half(p, x0, b, y, start=False) * half))
            out.append((f"bay{i}_{side(y)}_keystone", keystone.place(p, x0 + b / 2, y) * key))
        for k, u in enumerate(L.post_us(p, b)):
            d = L.cf_depth(p, b, u)
            cf = named(cross_frame.make(p, d), f"cross_frame_{b:.1f}mm_{k}")
            out.append((f"bay{i}_cross_frame_a{k}", cross_frame.place(p, x0 + u, d) * cf))
            out.append((f"bay{i}_cross_frame_b{k}", cross_frame.place(p, x0 + b - u, d) * cf))
        if L.mid_frame(p):
            d = L.mid_cf_depth(p, b)
            cf = named(cross_frame.make(p, d), f"cross_frame_{b:.1f}mm_mid")
            out.append((f"bay{i}_cross_frame_mid", cross_frame.place(p, x0 + b / 2, d) * cf))
    br = named(bracket.make(p), "bracket")
    for i, x in enumerate(xs):
        if (i == 0 and ends[0] == L.CORNER) or (i == len(xs) - 1 and ends[1] == L.CORNER):
            continue
        out.append((f"bracket{i}", bracket.place(p, x) * br))
    ep = named(end_pier.make(p), "end_pier")
    for y in p.rail_ys:
        if ends[0] == L.FREE:
            out.append((f"end_pier_start_{side(y)}", end_pier.place(p, xs[0], y, run_start=True) * ep))
        if ends[1] == L.FREE:
            out.append((f"end_pier_end_{side(y)}", end_pier.place(p, xs[-1], y, run_start=False) * ep))
    for k, seg in enumerate(L.segments(p, bays, ends)):
        lad = named(tie_ladder.painted(p, bays, seg, ends), f"ladder_{k:02d}")
        out.append((f"ladder{k}", tie_ladder.place(p, seg) * lad))
    for k, pc in enumerate(L.handrail_pieces(p, bays, ends)):
        hr = named(handrail.make(p, pc), f"handrail_{k:02d}")
        out.append((f"handrail{k}", handrail.place(p, pc) * hr))
    return out


def clashes(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> list[tuple[str, str, float]]:
    """Unplanned interference in a run. The cross-frames press onto the panels (and the mid-bay one over the
    keystones) on purpose when fit_cf < 0, so they're checked line-to-line here; press_fits shows those overlaps."""
    return find_clashes(placed_parts(replace(p, fit_cf=max(p.fit_cf, 0.0)), bays, ends))


def press_fits(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> list[tuple[str, str, float]]:
    """Every overlap at the real fits: the planned press fits (and anything clashes would also report)."""
    return find_clashes(placed_parts(p, bays, ends))


def make(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> Compound:
    # Copies share one shape, and STEP names the shared shape once, so children keep their part-type
    # label (set by named()); Onshape numbers the instances. Instance names stay in placed_parts().
    return Compound(children=[part for _, part in placed_parts(p, bays, ends)], label="run")

