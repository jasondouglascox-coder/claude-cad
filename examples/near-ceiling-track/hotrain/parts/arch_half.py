"""Half of one straight-run panel, pier at u=0, mid-bay at u=half. Two styles (`P.run_style`):
"arch" (half pier + top band + posts + half arch rib) or "deck_truss" (concrete-look half pier +
top chord + inclined end post + Warren web + bottom chord, spliced at mid-bay with a small bow-tie).

The deck truss carries rivet heads on its print-top face, which faces the room, and its concrete pier stands a
couple of layers proud of the steel there. A panel's start half is the end
half turned 180°, which would put its rivets on the wall side, so it prints as the mirror image instead
(`start=True`, placed with `place_half`)."""
import math

from build123d import Bezier, Circle, Face, Line, Location, Part, Plane, Pos, Rot, Sketch, Wire, extrude

from hotrain import layout as L
from hotrain.joints import butterfly, poly, rect
from hotrain.params import P, Params
from hotrain.parts import keystone


def _bar(a: tuple[float, float], b: tuple[float, float], w: float) -> Sketch:
    """Straight member of width w from a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ox, oy = -dy / n * w / 2, dx / n * w / 2
    return poly((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy))


def _shared(p: Params, bay_len: float) -> tuple[list, list]:
    """Tabs into the tie ladder, cross-frame notches, bracket tongue and latch window: every style."""
    adds = [rect(u - p.tab_len / 2, u + p.tab_len / 2, -1, p.tie_h) for u in L.tab_us(p, bay_len)]
    cuts = []
    nw = (p.cf_t + p.fit_slide) / 2
    for u in L.post_us(p, bay_len):  # cross-frame locating notch under the rib / bottom chord
        top = -L.cf_depth(p, bay_len, u) + p.rib_notch
        cuts.append(rect(u - nw, u + nw, L.rib_low(p, bay_len, u - nw) - 2, top))
    bw = (p.bracket_t + p.fit_slide) / 2
    cuts.append(rect(-1, bw, -p.pier_depth - 1, -p.pier_depth + p.pier_notch))  # bracket tongue
    cuts.append(rect(-1, bw, -p.latch_top - p.latch_win_h, -p.latch_top))  # latch window
    return adds, cuts


def end_post(p: Params, bay_len: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Deck truss inclined end post centerline: from the corner where the top chord meets the pier face
    (so its square-cut top end is buried in chord + cap, no tip poking out) down to the first post."""
    s, foot = L.springing_u(p), L.post_us(p, bay_len)[0]
    return (s, -p.top_band_h), (foot + p.dt_post_w / 2, -p.dt_depth + p.dt_chord_h / 2)


def deck_pier(p: Params) -> Sketch:
    """Concrete-look half pier (u >= 0) with its share of the top chord: cap ledge, battered face."""
    s, pd, tb, lap = L.springing_u(p), p.pier_depth, p.top_band_h, p.dt_lap
    zc = -tb - p.pier_cap_h
    return Sketch() + [rect(0, s, -tb, 0), rect(0, s + p.pier_cap_out, zc, -tb + lap),
                       poly((0, -pd), (s + p.pier_batter, -pd), (s, zc + 0.5), (0, zc + 0.5))]


def deck_profile(p: Params, bay_len: float) -> Sketch:
    """Profile in (u, z): u from the pier centerline, z = 0 at the tie underside."""
    h, s, pd, tb, lap = L.half_len(bay_len), L.springing_u(p), p.pier_depth, p.top_band_h, p.dt_lap
    dd, zb = p.dt_depth, -p.dt_depth + p.dt_chord_h  # truss depth, bottom chord top
    zc = -tb - p.pier_cap_h  # pier cap underside
    posts = L.post_us(p, bay_len)
    foot = posts[0]
    adds = [
        rect(0, h, -tb, 0),  # top chord
        rect(0, s + p.pier_cap_out, zc, -tb + lap),  # pier cap
        poly((0, -pd), (s + p.pier_batter, -pd), (s, zc + 0.5), (0, zc + 0.5)),  # battered pier body
        rect(foot - p.dt_post_w / 2 - 2.0, h, -dd, zb),  # bottom chord: walls both sides of the first cross-frame notch
        rect(h - p.dt_mid_w, h, -dd, 0),  # mid-bay post
        rect(h - p.dt_gusset_w, h, -dd, -dd + p.dt_gusset_h),  # splice plate
        _bar(*end_post(p, bay_len), p.dt_post_w),
    ]
    pts = posts + [h - p.dt_mid_w / 2]  # panel points; Warren apexes alternate bottom (at the foot) / top
    zs = [zb - lap / 2 if k % 2 == 0 else -tb + lap / 2 for k in range(len(pts))]
    for (a, za), (b, z2) in zip(zip(pts, zs), zip(pts[1:], zs[1:])):
        adds.append(_bar((a, za), (b, z2), p.dt_diag_w))
    for u in posts[1:]:
        adds.append(rect(u - p.dt_vert_w / 2, u + p.dt_vert_w / 2, zb - lap, -tb + lap))
    more, cuts = _shared(p, bay_len)
    cuts.append(Pos(h, keystone.key_z(p)) * butterfly(keystone.key_params(p), p.fit_snap))
    return (Sketch() + adds + more) - cuts


def profile(p: Params, bay_len: float) -> Sketch:
    if p.run_style == "arch":
        return arch_profile(p, bay_len)
    if p.run_style == "deck_truss":
        return deck_profile(p, bay_len)
    raise ValueError(f"run_style {p.run_style!r}: use 'arch' or 'deck_truss'")


def arch_profile(p: Params, bay_len: float) -> Sketch:
    """Profile in (u, z): u from the pier centerline, z = 0 at the band top (tie underside)."""
    h, s = L.half_len(bay_len), L.springing_u(p)
    mid, cd, pd = (s + h) / 2, p.crown_depth, p.pier_depth
    lo = Bezier((s, -pd), (mid, -cd), (h, -cd))
    hi = Bezier((h, -cd + p.rib_h), (mid, -cd + p.rib_h), (s, -pd + p.rib_h))
    rib = Face(Wire([lo, Line((h, -cd), (h, -cd + p.rib_h)), hi, Line((s, -pd + p.rib_h), (s, -pd))]))
    adds = [
        rect(0, h, -p.top_band_h, 0),  # top band
        rect(0, s, -pd, 0),  # half pier
        rib,
        rect(h - p.crown_block_w, h, -cd, 0),  # crown block holding the keystone socket
    ]
    for u in L.post_us(p, bay_len):
        adds.append(rect(u - p.post_w / 2, u + p.post_w / 2, L.rib_low(p, bay_len, u) + 1, -p.top_band_h / 2))
    more, cuts = _shared(p, bay_len)
    adds += more
    cuts.append(Pos(h, -cd / 2) * butterfly(p, p.fit_snap))  # keystone socket
    return (Sketch() + adds) - cuts


def _rows(p: Params, bay_len: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Rivet rows (u, z) on the deck truss: two along each chord and the end post, one along each vertical,
    diagonal and the mid-bay post, and a grid on the splice plate. The pier gets none (it's concrete)."""
    h, s, tb, lap = L.half_len(bay_len), L.springing_u(p), p.top_band_h, p.dt_lap
    dd, zb = p.dt_depth, -p.dt_depth + p.dt_chord_h
    posts = L.post_us(p, bay_len)
    u0 = s + p.pier_cap_out + p.rivet_d  # clear of the pier cap
    rows = [((u0, -tb * f), (h, -tb * f)) for f in (0.25, 0.75)]
    rows += [((posts[0] - p.dt_post_w / 2 - 2.0, -dd + p.dt_chord_h * f), (h, -dd + p.dt_chord_h * f)) for f in (0.25, 0.75)]
    (ax, az), (bx, bz) = end_post(p, bay_len)
    n = math.hypot(bx - ax, bz - az)
    ox, oz = -(bz - az) / n * p.dt_post_w / 4, (bx - ax) / n * p.dt_post_w / 4
    rows += [((ax + k * ox, az + k * oz), (bx + k * ox, bz + k * oz)) for k in (1, -1)]
    for u in posts[1:]:
        rows.append(((u, zb - lap), (u, -tb + lap)))
    pts = posts + [h - p.dt_mid_w / 2]
    zs = [zb - lap / 2 if k % 2 == 0 else -tb + lap / 2 for k in range(len(pts))]
    rows += [((a, za), (b, z2)) for (a, za), (b, z2) in zip(zip(pts, zs), zip(pts[1:], zs[1:]))]
    rows.append(((h - p.dt_mid_w / 2, -dd), (h - p.dt_mid_w / 2, 0)))
    g = p.dt_gusset_w
    rows += [((h - g * f, -dd), (h - g * f, -dd + p.dt_gusset_h)) for f in (0.3, 0.65)]
    return rows


def rivet_points(p: Params, bay_len: float) -> list[tuple[float, float]]:
    """(u, z) of every rivet head: along the rows at rivet_pitch, kept where the whole head (plus a margin) stands on
    the panel, and never touching another head. Empty for the arch style or rivet_d = 0."""
    if p.run_style != "deck_truss" or p.rivet_d <= 0:
        return []
    bare = Pos(0, p.pier_depth, 0) * extrude(profile(p, bay_len), p.panel_t)
    r, mid = p.rivet_d / 2 + p.rivet_margin, p.panel_t / 2
    ring = [(0.0, 0.0)] + [(r * math.cos(k * math.pi / 8), r * math.sin(k * math.pi / 8)) for k in range(16)]
    on = lambda u, z: all(bare.is_inside((u + du, z + dz + p.pier_depth, mid)) for du, dz in ring)
    keep, gap = [], p.rivet_d + 0.3
    pier = L.springing_u(p) + p.pier_cap_out + p.rivet_d  # concrete: the pier and its cap stay bare
    posts = L.post_us(p, bay_len)  # cross-frames grip both panels here
    under = lambda u: any(abs(u - x) < (p.cf_t + p.fit_slide) / 2 + p.rivet_d / 2 + p.rivet_margin for x in posts)
    for (a, za), (b, zb) in _rows(p, bay_len):
        n = max(1, int(math.hypot(b - a, zb - za) // p.rivet_pitch))
        for k in range(n + 1):
            u, z = a + (b - a) * k / n, za + (zb - za) * k / n
            if u > pier and not under(u) and on(u, z) and all((u - c) ** 2 + (z - d) ** 2 >= gap ** 2 for c, d in keep):
                keep.append((u, z))
    return keep


def pier_face(p: Params, bay_len: float) -> Sketch:
    """(u, z) of the concrete pier's raised room face: its body and cap up to the top chord's underside, inside the
    panel's outline, except the strip the bracket (or a corner anchor) grips at the pier centerline."""
    s, pd, tb = L.springing_u(p), p.pier_depth, p.top_band_h
    zc = -tb - p.pier_cap_h
    pier = Sketch() + [poly((0, -pd), (s + p.pier_batter, -pd), (s, zc + 0.5), (0, zc + 0.5)),
                       rect(0, s + p.pier_cap_out, zc, -tb)]
    grip = (p.bracket_t + p.fit_slide) / 2 + 0.3
    return (pier & profile(p, bay_len)) - rect(-1, grip, -pd - 1, 1)


def mirrored(p: Params) -> bool:
    """Deck truss panels print a mirror-image start half, so both halves' rivets face the room."""
    return p.run_style == "deck_truss"


def make(p: Params = P, bay_len: float = P.bay_len, start: bool = False) -> Part:
    """Print orientation: flat on the bed, u along X, pier bottom on Y=0; rivet heads (deck truss) on top. start: the
    mirror image for a panel's start half (pier at X = half length), see place_half."""
    part = Pos(0, p.pier_depth, 0) * extrude(profile(p, bay_len), p.panel_t)
    proud = []
    pts = rivet_points(p, bay_len)
    if pts:
        heads = Sketch() + [Pos(u, z + p.pier_depth) * Circle(p.rivet_d / 2) for u, z in pts]
        proud.append(Pos(0, 0, p.panel_t - 0.01) * extrude(heads, p.printer.layers(p.rivet_h) + 0.01))
    if p.run_style == "deck_truss" and p.pier_relief > 0:
        face = Pos(0, p.pier_depth) * pier_face(p, bay_len)
        proud.append(Pos(0, 0, p.panel_t - 0.01) * extrude(face, p.printer.layers(p.pier_relief) + 0.01))
    if proud:
        part = Part((part + proud).solids())
    if start and mirrored(p):
        part = Pos(L.half_len(bay_len), 0, 0) * part.mirror(Plane.YZ)
    return part


def place_half(p: Params, x0: float, bay_len: float, y_c: float, start: bool) -> Location:
    """Location for make(p, bay_len, start): the end half as place(end=True); the mirrored start half turned so its
    top (rivet) face looks toward +Y, the room, like the end half's."""
    if not start:
        return place(p, x0, bay_len, y_c, end=True)
    if not mirrored(p):
        return place(p, x0, bay_len, y_c, end=False)
    centre = Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
    return Pos(x0 + L.half_len(bay_len), y_c, -p.pier_depth) * Rot(0, 0, 180) * centre


def place(p: Params, x0: float, bay_len: float, y_c: float, end: bool) -> Location:
    """Location taking the print-frame part into the run frame. end=True mirrors it to the bay's far half."""
    centre = Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
    if end:
        return Pos(x0 + bay_len, y_c, -p.pier_depth) * Rot(0, 0, 180) * centre
    return Pos(x0, y_c, -p.pier_depth) * centre
