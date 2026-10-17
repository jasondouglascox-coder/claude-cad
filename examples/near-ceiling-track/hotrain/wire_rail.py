"""Stainless wire rail on a printed web: the web's cross-section, the wheel keep-outs it must clear, NMRA RP-25 wheel
profiles, and the gauge those wheels feel on a round railhead. Pure 2D math plus a few faces; no assemblies.
docs/specs/2026-10-16-wire-rail-design.md

Rail coordinates: x toward the field side, z up, origin at the wire's top (the rail top); the wire centre is at
(0, -wire_d/2), so its gauge face is at x = -wire_d/2.
Wheel coordinates: u across the tire from the back face outward, rad from the axle."""
import math

from build123d import Axis, Face, Part, Plane, Vector, Wire, revolve

from cadkit import Printer
from hotrain.params import INCH, Params


def fine_printer(p: Params) -> Printer:
    """The A1 at the web's fine layers (the test plates' slicer settings match)."""
    return Printer(bed=p.bed, bed_y=None if p.bed_y == p.bed else p.bed_y, margin=p.bed_margin,
                   layer=p.wire_layer, first_layer=p.wire_first_layer)


def y_wire(p: Params) -> float:
    """Track centre to a wire centre."""
    return p.gauge / 2 + p.wire_d / 2


def _layer_below(p: Params, z: float) -> float:
    """Highest fine-layer boundary at or under z (absolute height)."""
    fp = fine_printer(p)
    k = math.floor((z - fp.first) / fp.layer + 1e-9)
    return round(fp.first + k * fp.layer, 6)


def profile_pts(p: Params, n: int = 48) -> list[tuple[float, float]]:
    """The gray web: a foot on the runner, a cradle touching the wire's bottom, and a field lip as high as the tread
    allows (two lines wide, vertical outside). On the gauge side the 1.6 mm deep-flange keep-out leaves no room
    for a wall beside the wire: just a step under it, one layer below the wire's bottom, then the low shelf."""
    r = p.wire_d / 2
    rc = r + p.wire_seat_fit
    zc = -p.wire_d + rc  # cradle centre: the cradle's bottom is the wire's bottom
    zb = p.tie_h - p.rail_top
    zf = _layer_below(p, p.rail_top - p.tread_keepout - 1e-6) - p.rail_top
    zg = _layer_below(p, p.rail_top - p.flange_depth_max - 1e-6) - p.rail_top
    zs = _layer_below(p, p.rail_top - p.wire_d - 1e-6) - p.rail_top  # the step under the wire's gauge half
    xf = math.sqrt(rc * rc - (zf - zc) ** 2)
    xs = -r + p.wire_step_gap
    af = math.atan2(zf - zc, xf)
    arc = [(rc * math.cos(af + (-math.pi / 2 - af) * i / n), zc + rc * math.sin(af + (-math.pi / 2 - af) * i / n))
           for i in range(n + 1)]  # field lip down to the cradle's bottom
    hb = p.wire_base_w / 2
    xo = max(hb, xf + p.wire_lip_w)  # field face: vertical, so the lip only widens below its top
    return [(-hb, zb), (xo, zb), (xo, zf)] + arc + [(0.0, zs), (xs, zs), (xs, zg), (-hb, zg)]


def envelopes(p: Params) -> dict[str, list[tuple[float, float]]]:
    """Where the wheels go: the deep-flange zone inside the gauge face and the tread zone above the field side."""
    r, f = p.wire_d / 2, p.flange_depth_max
    tread_x = -r + p.wheel_n + 0.010 * INCH
    return {"flange": [(-r - f, -f), (-r, -f), (-r, 1.0), (-r - f, 1.0)],
            "tread": [(-r, -p.tread_keepout), (tread_x, -p.tread_keepout), (tread_x, 1.0), (-r, 1.0)]}


def face(pts) -> Face:
    return Face(Wire.make_polygon([Vector(x, y, 0) for x, y in pts], close=True))


def check_envelopes(pts, p: Params) -> dict[str, float]:
    """Area (mm^2) of the profile inside each wheel keep-out: all zero or a wheel hits plastic."""
    prof, out = face(pts), {}
    for name, env in envelopes(p).items():
        x = prof & face(env)
        out[name] = x.area if x is not None else 0.0
    return out


# --- wheels ----------------------------------------------------------------------------------------------------
def flange_end(p: Params) -> float:
    """u where the root fillet meets the tread."""
    return p.wheel_t + p.wheel_p


def wheel_pts(p: Params, depth: float) -> list[tuple[float, float]]:
    """RP-25 Code 110 contour with a flange `depth` deep: round flange tip as wide as T, a fillet from the gaging
    point P into a tapered tread, a dished face and a hub on the axle."""
    rw, tip, t, pp, n = p.wheel_dia / 2, p.wheel_t / 2, p.wheel_t, p.wheel_p, p.wheel_n
    c = (tip, rw + depth - tip)
    pts = [(0.0, p.axle_d / 2), (0.0, c[1])]
    pts += [(c[0] - tip * math.cos(math.pi * i / 16), c[1] + tip * math.sin(math.pi * i / 16)) for i in range(1, 16)]
    pts.append((t, c[1]))
    if c[1] > rw + pp + 1e-9:
        pts.append((t, rw + pp))
    f = (t + pp, rw + pp)
    pts += [(f[0] - pp * math.cos(math.pi / 2 * i / 8), f[1] - pp * math.sin(math.pi / 2 * i / 8)) for i in range(1, 9)]
    taper = math.tan(math.radians(p.wheel_taper))
    u1 = n - 0.13
    pts += [(u1, rw - taper * (u1 - f[0])), (n, rw - taper * (n - f[0]) - 0.13)]
    pts += [(n, rw - 0.9), (n - 0.6, rw - 1.15), (n - 0.6, 2.0), (n, 1.8), (n, p.axle_d / 2)]
    return pts


def wheel_solid(p: Params, depth: float) -> Part:
    """The wheel as a solid, axle along +Z, u = z."""
    return revolve(Plane.XZ * face([(rad, u) for u, rad in wheel_pts(p, depth)]), Axis.Z, 360)


def _radius_at(pts, u: float) -> float:
    best = 0.0
    for (u0, r0), (u1, r1) in zip(pts, pts[1:] + pts[:1]):
        if u0 != u1 and min(u0, u1) <= u <= max(u0, u1):
            best = max(best, r0 + (r1 - r0) * (u - u0) / (u1 - u0))
    return best


def ride_height(p: Params, depth: float, shift: float) -> float:
    """Axle centre above the rail top with both treads on the wires (wheelset shifted `shift` toward +y)."""
    wp, r, best = wheel_pts(p, depth), p.wire_d / 2, -1.0
    for side in (1, -1):
        for i in range(-200, 201):
            x = r * i / 200
            u = y_wire(p) + x - p.wheel_b / 2 - side * shift
            if flange_end(p) < u <= p.wheel_n:
                best = max(best, -(r - math.sqrt(r * r - x * x)) + _radius_at(wp, u))
    return best


def _section(p: Params, depth: float, shift: float) -> list[tuple[float, float, float]]:
    """(x, z, u) of the +y wheel's contour in that rail's coordinates."""
    zc = ride_height(p, depth, shift)
    return [(u + p.wheel_b / 2 + shift - y_wire(p), zc - rad, u) for u, rad in wheel_pts(p, depth)]


def _nearest(p: Params, depth: float, shift: float) -> tuple[float, tuple[float, float]]:
    """Gap from the flange (and its fillet) to the wire, and the nearest flange point."""
    centre, r = (0.0, -p.wire_d / 2), p.wire_d / 2
    sec = _section(p, depth, shift)
    best = (math.inf, (0.0, 0.0))
    for a, b in zip(sec, sec[1:]):
        if a[2] > flange_end(p) + 1e-9 or b[2] > flange_end(p) + 1e-9 or min(a[1], b[1]) > 1.0:
            continue
        dx, dz = b[0] - a[0], b[1] - a[1]
        t = max(0.0, min(1.0, ((centre[0] - a[0]) * dx + (centre[1] - a[1]) * dz) / (dx * dx + dz * dz or 1)))
        q = (a[0] + t * dx, a[1] + t * dz)
        d = math.dist(q, centre) - r
        if d < best[0]:
            best = (d, q)
    return best


def max_shift(p: Params, depth: float) -> float:
    """How far the wheelset slides from centre before this flange meets its wire."""
    lo, hi = 0.0, 1.5
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _nearest(p, depth, mid)[0] > 0 else (lo, mid)
    return lo


def effective_gauge(p: Params, depth: float) -> float:
    """The gauge the flanges feel: their span at the gaging point plus the play both ways."""
    return p.wheel_b + 2 * p.wheel_t + 2 * max_shift(p, depth)


def contact_angle(p: Params, depth: float) -> float:
    """Flange contact angle (degrees from horizontal) against the wire at full shift: higher resists climbing."""
    _, q = _nearest(p, depth, max_shift(p, depth))
    nx, nz = q[0], q[1] + p.wire_d / 2
    return 90.0 - math.degrees(math.atan2(nz, abs(nx)))
