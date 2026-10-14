"""Every part of a run placed where it goes, for Onshape review and interference checks."""
import itertools

from build123d import Compound, Part

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
        for y in p.rail_ys:
            out.append((f"bay{i}_{side(y)}_arch_start", arch_half.place(p, x0, b, y, end=False) * half))
            out.append((f"bay{i}_{side(y)}_arch_end", arch_half.place(p, x0, b, y, end=True) * half))
            out.append((f"bay{i}_{side(y)}_keystone", keystone.place(p, x0 + b / 2, y) * key))
        for k, u in enumerate(L.post_us(p, b)):
            d = L.cf_depth(p, b, u)
            cf = named(cross_frame.make(p, d), f"cross_frame_{b:.1f}mm_{k}")
            out.append((f"bay{i}_cross_frame_a{k}", cross_frame.place(p, x0 + u, d) * cf))
            out.append((f"bay{i}_cross_frame_b{k}", cross_frame.place(p, x0 + b - u, d) * cf))
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


def make(p: Params = P, bays: list[float] = L.BAYS, ends: tuple = L.RUN_ENDS) -> Compound:
    # Copies share one shape, and STEP names the shared shape once, so children keep their part-type
    # label (set by named()); Onshape numbers the instances. Instance names stay in placed_parts().
    return Compound(children=[part for _, part in placed_parts(p, bays, ends)], label="run")


def _boxes_overlap(a, b) -> bool:
    lo_a, hi_a, lo_b, hi_b = a.min, a.max, b.min, b.max
    return (lo_a.X < hi_b.X and lo_b.X < hi_a.X and lo_a.Y < hi_b.Y and lo_b.Y < hi_a.Y
            and lo_a.Z < hi_b.Z and lo_b.Z < hi_a.Z)


def find_clashes(items: list[tuple[str, Part]], tol: float = 1e-3) -> list[tuple[str, str, float]]:
    """Pairs of parts sharing more than tol mm^3 of volume. Touching faces don't count."""
    boxes = [(n, s, s.bounding_box()) for n, s in items]
    out = []
    for (na, a, ba), (nb, b, bb) in itertools.combinations(boxes, 2):
        if _boxes_overlap(ba, bb):
            v = (a & b).volume
            if v > tol:
                out.append((na, nb, round(v, 4)))
    return out
