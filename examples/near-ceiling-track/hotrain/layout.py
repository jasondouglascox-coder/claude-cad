"""Pure layout math: where ties, tabs, posts, piers and ladder joints go. No CAD here.

Run frame: X along the track (0 = first pier centerline), Y across (+ toward the room),
Z up (0 = tie underside = top of the arch panels' top band).
"""
import math
from dataclasses import dataclass

from hotrain.params import INCH, P, Params

# The run you are building, as stud-to-stud bay lengths (mm). Prototype: one 16" bay.
BAYS: list[float] = [16 * INCH]

# What each end of the run meets: FREE (end pier + bracket) or CORNER (the corner's rod anchor replaces
# the bracket; the deck stops at the anchor). Prototype: free at both ends.
FREE, CORNER = "free", "corner"
RUN_ENDS: tuple[str, str] = (FREE, FREE)


@dataclass(frozen=True)
class Tie:
    x: float
    long: bool
    lip: bool
    gap: bool = False  # left out of the ladder: solder gap at the bay's mid


@dataclass(frozen=True)
class HandrailPiece:
    """One printed handrail piece: owns the posts listed; its bars stop just short of the next piece's first post."""
    x_start: float
    x_end: float
    posts: tuple


@dataclass(frozen=True)
class Segment:
    """One tie ladder (and the handrail piece above it)."""
    x_start: float
    x_end: float
    female_start: bool  # jigsaw socket at x_start (another ladder plugs in)
    male_end: bool  # jigsaw tab at x_end (into the next ladder, or a corner's end deck)
    male_start: bool = False  # jigsaw tab pointing back out of x_start, into a corner's end deck


def validate_bays(p: Params, bays: list[float]) -> None:
    """Fail loudly on a bay list that can't be printed, instead of exporting a broken part."""
    if not bays:
        raise ValueError("BAYS is empty: list at least one stud-to-stud bay length in mm")
    for i, b in enumerate(bays):
        if not p.min_bay_len <= b <= p.max_bay_len:
            raise ValueError(f"bay {i} is {b:.1f} mm; each bay must be {p.min_bay_len:.1f}-{p.max_bay_len:.1f} mm "
                             f"(add a drywall-anchored pier to split a longer span)")


def half_len(bay_len: float) -> float:
    return bay_len / 2


def springing_u(p: Params = P) -> float:
    return p.pier_w / 2


def rib_low(p: Params, bay_len: float, u: float) -> float:
    """Z of the panel's lowest material at half-local u (0 = pier centerline, half_len = mid-bay).
    Arch: the rib underside. Deck truss: the pier, then the inclined end post, then the bottom chord."""
    if p.run_style == "deck_truss":
        return _deck_low(p, bay_len, u)
    s, h = springing_u(p), half_len(bay_len)
    t = (u - s) / (h - s)
    return -p.crown_depth - (p.pier_depth - p.crown_depth) * (1 - t) ** 2


def _deck_low(p: Params, bay_len: float, u: float) -> float:
    s = springing_u(p) + p.pier_batter
    foot = post_us(p, bay_len)[0] - p.dt_post_w
    if u <= s:
        return -p.pier_depth
    if u >= foot:
        return -p.dt_depth
    z_top = -p.top_band_h - p.pier_cap_h  # end post springs from under the pier cap
    return z_top + (u - s) / (foot - s) * (-p.dt_depth - z_top)


def cf_depth(p: Params, bay_len: float, u: float) -> float:
    """Cross-frame depth at post u: down to the higher (crown-side) edge of the rib under the frame,
    so the rib notch keeps a full rib_notch wall on both sides of the frame."""
    nw = (p.cf_t + p.fit_slide) / 2
    return -max(rib_low(p, bay_len, u - nw), rib_low(p, bay_len, u + nw))


def mid_frame(p: Params) -> bool:
    """Deck truss: a cross-frame also straddles the mid-bay splice (the arch's crown block stays bare)."""
    return p.run_style == "deck_truss"


def frame_us(p: Params, bay_len: float) -> list[float]:
    """Half-local u of every cross-frame a half carries a notch for: the posts, and mid-bay (deck truss)."""
    return post_us(p, bay_len) + [half_len(bay_len)] * mid_frame(p)


def mid_cf_depth(p: Params, bay_len: float) -> float:
    """Depth of the mid-bay cross-frame: it seats in a notch split between the two halves, like the posts' frames."""
    return cf_depth(p, bay_len, half_len(bay_len))


def bay_pitch(p: Params, bay_len: float) -> float:
    """Tie pitch adjusted so the bay holds a whole number of ties."""
    return bay_len / ties_per_bay(p, bay_len)


def ties_per_bay(p: Params, bay_len: float) -> int:
    """A whole multiple of long_tie_every, so handrail posts keep one spacing across every pier."""
    e = p.long_tie_every
    return e * max(1, round(bay_len / p.tie_pitch / e))


def joint_u(p: Params, bay_len: float) -> float:
    """Half-local u of the ladder joint near the quarter point (mid-gap between ties)."""
    pb = bay_pitch(p, bay_len)
    return pb * math.floor(bay_len / 4 / pb + 0.5)


def post_us(p: Params, bay_len: float) -> list[float]:
    h = half_len(bay_len)
    out, k = [], 1
    while k * p.post_pitch + p.post_w / 2 < h - p.crown_block_w:
        out.append(k * p.post_pitch)
        k += 1
    return out


def tab_us(p: Params, bay_len: float) -> list[float]:
    h, uj = half_len(bay_len), joint_u(p, bay_len)
    out, u = [], p.tab_first
    while u + p.tab_len / 2 <= h - p.crown_block_w - 1:
        if abs(u - uj) >= p.tab_len / 2 + p.tab_joint_keepout:
            out.append(u)
        u += p.tab_pitch
    return out


def pier_xs(bays: list[float]) -> list[float]:
    xs = [0.0]
    for b in bays:
        xs.append(xs[-1] + b)
    return xs


def rod_tail_spans(p: Params, bays: list[float], ends: tuple = RUN_ENDS) -> list[tuple[float, float]]:
    """x ranges (run frame) where a corner's aluminum rods reach into this run past its anchor."""
    lo, hi = run_extent(p, bays, ends)
    out = []
    if ends[0] == CORNER:
        out.append((lo - 1.0, lo + p.rod_tail + 1.0))
    if ends[1] == CORNER:
        out.append((hi - p.rod_tail - 1.0, hi + 1.0))
    return out


def run_extent(p: Params, bays: list[float], ends: tuple = RUN_ENDS) -> tuple[float, float]:
    lo = -p.pier_w / 2 if ends[0] == FREE else 0.0
    hi = sum(bays) + (p.pier_w / 2 if ends[1] == FREE else 0.0)
    return lo, hi


def ties(p: Params, bays: list[float], ends: tuple = RUN_ENDS) -> list[Tie]:
    """Every tie in the run. Tie index k counts per bay (negative / past n over the end piers);
    long ties (handrail posts) are k % long_tie_every == long_tie_every // 2, which keeps one
    post spacing across piers and onto the end piers."""
    e = p.long_tie_every
    is_post = lambda k: k % e == e // 2
    out: list[Tie] = []
    x_lo, x_hi = run_extent(p, bays, ends)
    pb0 = bay_pitch(p, bays[0])
    m = 0
    while -pb0 * (m + 0.5) - p.tie_w / 2 >= x_lo:  # ties over the start end pier
        out.insert(0, Tie(-pb0 * (m + 0.5), is_post(-m - 1), False))
        m += 1
    for x0, b in zip(pier_xs(bays), bays):
        pb, n = bay_pitch(p, b), ties_per_bay(p, b)
        gap = set()
        if p.solder_gap:  # plain ties between the neighbouring post ties nearest mid-bay
            posts = [k for k in range(n) if is_post(k)]
            pairs = [(a, b) for a, b in zip(posts, posts[1:])]
            if pairs:
                a, b = min(pairs, key=lambda ab: abs((ab[0] + ab[1]) / 2 + 0.5 - n / 2))
                gap = set(range(a + 1, b))
        for k in range(n):
            out.append(Tie(x0 + pb * (k + 0.5), is_post(k), k % p.spike_lip_every == 0, k in gap))
    xl, pbl, nl = sum(bays), bay_pitch(p, bays[-1]), ties_per_bay(p, bays[-1])
    m = 0
    while xl + pbl * (m + 0.5) + p.tie_w / 2 <= x_hi:  # ties over the far end pier
        out.append(Tie(xl + pbl * (m + 0.5), is_post(nl + m), False))
        m += 1
    return out


def segments(p: Params, bays: list[float], ends: tuple = RUN_ENDS) -> list[Segment]:
    x_lo, x_hi = run_extent(p, bays, ends)
    cuts = [x_lo]
    for x0, b in zip(pier_xs(bays), bays):
        uj = joint_u(p, b)
        cuts += [x0 + uj, x0 + b - uj]
    cuts.append(x_hi)
    n = len(cuts) - 1
    return [Segment(cuts[i], cuts[i + 1], i > 0, i < n - 1 or ends[1] == CORNER, i == 0 and ends[0] == CORNER)
            for i in range(n)]


def tab_xs(p: Params, bays: list[float]) -> list[float]:
    out = []
    for x0, b in zip(pier_xs(bays), bays):
        for u in tab_us(p, b):
            out += [x0 + u, x0 + b - u]
    return sorted(out)


def handrail_pieces(p: Params, bays: list[float], ends: tuple = RUN_ENDS) -> list[HandrailPiece]:
    """Split the handrail at the post nearest each ladder joint, keeping every piece on the bed."""
    posts = [t.x for t in ties(p, bays, ends) if t.long]
    hw = p.handrail_post_w / 2
    starts = [0]
    for j in (s.x_end for s in segments(p, bays, ends)[:-1]):
        i = min(range(len(posts)), key=lambda i: abs(posts[i] - j))
        while i > starts[-1] + 1 and posts[i] - p.handrail_gap - posts[starts[-1]] > p.bed_usable:
            i -= 1
        if i > starts[-1]:
            starts.append(i)
    pieces = []
    for a, b in zip(starts, starts[1:] + [None]):
        owned = posts[a:b]
        x1 = posts[b] - hw - p.handrail_gap if b is not None else owned[-1] + hw
        pieces.append(HandrailPiece(owned[0] - hw, x1, tuple(owned)))
    return pieces
