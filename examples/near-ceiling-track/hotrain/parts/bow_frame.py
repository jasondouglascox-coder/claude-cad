"""Corner side frame. Its outer face runs down past the deck edge, and two ledges on its inner face (above
and below the tie band) form a U the deck's tie ends slide into, glued. Printed outer face down, so the
U opens upward and needs no supports; all gray, one color.

Two styles (`P.corner_style`): a Pratt pony truss (inclined end posts, verticals, diagonals sloping
down toward mid-span, open top) or the original bowstring (bottom chord, arch rib, hangers).
"""
import math

from build123d import Bezier, Face, Line, Part, Pos, Sketch, Wire, extrude

from hotrain.joints import poly, rect
from hotrain.params import P, Params


def tab_xs(p: Params, length: float) -> list[float]:
    return [length / 4, length / 2, 3 * length / 4]


def u_bottom(p: Params) -> float:
    """Bottom of the frame (and its lower ledge), z = 0 at the tie underside."""
    return -p.fit_slide - p.frame_ledge_lo


def top_z(p: Params) -> float:
    """Top of the frame, z = 0 at the tie underside."""
    return p.rail_top + (p.truss_rise if p.corner_style == "pony" else p.bow_rise)


def _bar(a: tuple[float, float], b: tuple[float, float], w: float) -> Sketch:
    """Straight member of width w from a to b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ox, oy = -dy / n * w / 2, dx / n * w / 2
    return poly((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy))


def _skirt(p: Params, length: float, z0: float) -> list[Sketch]:
    """Outer face carried down past the deck edge to the bottom of the U, except at each end, where the
    frame sits on the floor beam (the step locates the span along the track)."""
    e = p.frame_ledge_end
    return [rect(e, length - e, u_bottom(p), z0 + 0.5), rect(0, length, p.fit_slide, z0 + 0.5)]


def pony_profile(p: Params, length: float) -> Sketch:
    """(x, z): bottom chord on the edge beam, Pratt web, inclined end posts, horizontal top chord."""
    z0 = p.tie_h
    zc = z0 + p.bow_chord_h  # bottom chord top
    zt = top_z(p)
    zb = zt - p.truss_chord_w  # top chord underside
    n, pw = p.truss_panels, p.truss_post_w
    xs = [length * k / n for k in range(n + 1)]  # panel points
    lap = 1.0  # members overlap the chords so joints are real areas, not edges
    shapes = [rect(0, length, z0, zc), rect(xs[1] - lap, xs[-2] + lap, zb, zt)]
    # inclined end posts: bottom chord end up to the first/last top panel point
    lean = pw / 2 / math.sin(math.atan2(zt - z0, xs[1]))  # horizontal half-width of the sloped post
    shapes.append(poly((0, z0), (2 * lean, z0), (xs[1] + lean, zt), (xs[1] - lean, zt)))
    shapes.append(poly((length - 2 * lean, z0), (length, z0), (xs[-2] + lean, zt), (xs[-2] - lean, zt)))
    for x in xs[2:-2]:
        shapes.append(rect(x - p.truss_vert_w / 2, x + p.truss_vert_w / 2, zc - lap, zb + lap))
    # verticals next to the end posts carry the first floor panel point (hip verticals)
    for x in (xs[1], xs[-2]):
        shapes.append(rect(x - p.truss_vert_w / 2, x + p.truss_vert_w / 2, zc - lap, zb + lap))
    half = n // 2
    for k in range(1, half):  # left half: top of panel point k down to bottom of k+1
        shapes.append(_bar((xs[k], zb + lap / 2), (xs[k + 1], zc - lap / 2), p.truss_diag_w))
        shapes.append(_bar((xs[n - k], zb + lap / 2), (xs[n - k - 1], zc - lap / 2), p.truss_diag_w))
    g = p.truss_gusset
    for x in xs[1:-1]:  # gussets under the top chord and over the bottom chord at each vertical
        for sgn in (1, -1):
            shapes.append(poly((x, zb + 0.2), (x + sgn * g, zb + 0.2), (x, zb - g)))
            shapes.append(poly((x, zc - 0.2), (x + sgn * g, zc - 0.2), (x, zc + g)))
    return Sketch() + shapes + _skirt(p, length, z0)


def bow_profile(p: Params, length: float) -> Sketch:
    """(x, z) with z = 0 at the tie underside; the frame stands on the edge beam top (z = tie_h)."""
    z0 = p.tie_h
    zc = z0 + p.bow_chord_h
    zs = zc + 4  # springing
    zt = p.rail_top + p.bow_rise  # crown, top of rib
    pw, rw = p.bow_post_w, p.bow_rib_w
    lo_mid = 2 * (zt - rw) - zs  # quadratic Bezier control so the curve peaks at zt - rw
    lo = Bezier((pw, zs), (length / 2, lo_mid), (length - pw, zs))
    hi = Bezier((length - pw, zs + rw), (length / 2, lo_mid + rw), (pw, zs + rw))  # lower edge + rw
    rib = Face(Wire([lo, Line((length - pw, zs), (length - pw, zs + rw)), hi, Line((pw, zs + rw), (pw, zs))]))
    shapes = [rect(0, length, z0, zc), rect(0, pw, z0, zs + rw), rect(length - pw, length, z0, zs + rw), rib]
    n = p.bow_panels
    for k in range(1, n):
        x = pw + k * (length - 2 * pw) / n
        t = (x - pw) / (length - 2 * pw)
        z_rib = (1 - t) ** 2 * zs + 2 * t * (1 - t) * lo_mid + t * t * zs
        shapes.append(rect(x - p.bow_hanger_w / 2, x + p.bow_hanger_w / 2, zc - 0.5, z_rib + 0.5))
    return Sketch() + shapes + _skirt(p, length, z0)


def profile(p: Params, length: float) -> Sketch:
    if p.corner_style == "pony":
        return pony_profile(p, length)
    if p.corner_style == "bowstring":
        return bow_profile(p, length)
    raise ValueError(f"corner_style {p.corner_style!r}: use 'pony' or 'bowstring'")


def ledges(p: Params, length: float) -> Sketch:
    """(x, z) of the two inward ledges: over the ties full length, under the ties clear of the floor beams."""
    f, e = p.fit_slide, p.frame_ledge_end
    return Sketch() + [rect(0, length, p.tie_h + f, p.tie_h + f + p.frame_ledge_hi),
                       rect(e, length - e, -f - p.frame_ledge_lo, -f)]


def make(p: Params = P, length: float = 160.0) -> Part:
    """Print orientation: outer face down (Z = 0), x along the frame, Y = height above the frame bottom
    (z = u_bottom); the web is bow_frame_t thick and the ledges add frame_ledge on top (the inner side)."""
    t = p.bow_frame_t
    web = extrude(profile(p, length), t)
    led = Pos(0, 0, t - 0.5) * extrude(ledges(p, length), p.frame_ledge + 0.5)
    return Pos(0, -u_bottom(p), 0) * Part((web + led).solids())
