"""Ceiling gauge: a T held against the ceiling, with a pencil hole at each bracket screw line, so every
bracket and rod anchor is marked at the same height round the room. Gauge frame: x down from the ceiling (the T's
top edge at x = 0), y across, z out of the wall. Longer than the bed, so it prints as the T (bar, braces, a stub)
and the arm (both holes), joined by a glued dovetail at x = gauge_split.

With a bar the arm becomes an L that marks each bracket from the one before: the bar runs out from the arm at the top
hole's height to a hook (keyhole) one bay along, at each bay length. Hooked on the previous bracket's top screw
(10" down) and pushed up until the T meets the ceiling, it can only sit level, so both holes mark the next
bracket's screws. On its own, the arm against the ceiling marks the first bracket. Three glued pieces: the T, the
corner (arm, near half of the bar, a brace) and the bar's end (the hooks)."""
from build123d import Circle, Part, Pos, Rot, Sketch, extrude

from cadkit.shapes import dovetail, pencil_hole
from hotrain.joints import poly, rect
from hotrain.params import P, Params


def hole_xs(p: Params) -> list[float]:
    """Top and bottom screw centers below the ceiling."""
    return [p.screw_below_ceiling, p.screw_below_ceiling + p.screw_zs[1] - p.screw_zs[0]]


def _length(p: Params) -> float:
    return hole_xs(p)[-1] + p.gauge_tail


def _tab(p: Params, clearance: float = 0.0, x: float | None = None) -> Sketch:
    x = p.gauge_split if x is None else x
    return dovetail(x, 0, p.gauge_jig_neck, p.gauge_jig_head, p.gauge_jig_len, clearance)


def _pencil_holes(p: Params) -> list[Part]:
    """A throat at the wall a nail or pencil point pokes through, under a cone that guides it down."""
    return [Pos(x, 0) * pencil_hole(p.gauge_throat_d, p.gauge_throat_h, p.gauge_t) for x in hole_xs(p)]


def _brace(p: Params, s: int) -> Sketch:
    """45 degrees from the bar's end (under the bar) to the arm's edge."""
    h, a, w = p.gauge_bar_l / 2, p.gauge_arm_w / 2, p.gauge_brace_w / 2
    x0, x1 = p.gauge_bar_w, p.gauge_bar_w + (h - a)
    return poly((x0 - w, s * h), (x0 + w, s * h), (x1 + w, s * a), (x1 - w, s * a))


def t_in_gauge(p: Params = P) -> Part:
    a = p.gauge_arm_w / 2
    sk = Sketch() + [rect(0, p.gauge_bar_w, -p.gauge_bar_l / 2, p.gauge_bar_l / 2),
                     rect(0, p.gauge_split, -a, a), _brace(p, 1), _brace(p, -1), _tab(p)]
    return extrude(sk & rect(0, p.gauge_split + p.gauge_jig_len + 1, -p.gauge_bar_l / 2, p.gauge_bar_l / 2), p.gauge_t)


def arm_in_gauge(p: Params = P) -> Part:
    a = p.gauge_arm_w / 2
    sk = rect(p.gauge_split, _length(p), -a, a) - _tab(p, p.gauge_fit)
    return extrude(sk, p.gauge_t) - _pencil_holes(p)


def assembled(p: Params = P) -> Part:
    return t_in_gauge(p) + arm_in_gauge(p)


def _flat(part: Part) -> Part:
    bb = part.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, 0) * part


def t_piece(p: Params = P) -> Part:
    """Print orientation: flat on the bed."""
    return _flat(t_in_gauge(p))



def bay_pitches(p: Params = P) -> list[float]:
    """Pier to pier along each kind of run (the room's bay lengths), shortest first."""
    from hotrain import room
    return sorted({round(b, 2) for s in room.sections(p) if s.kind == "run" for b in s.bays})


def pivot_ys(p: Params) -> list[float]:
    """Where the L hooks on the previous bracket's top screw: one bay along the wall from the arm, at each bay
    length (shortest first)."""
    return [-b for b in bay_pitches(p)]


def entry_dy(p: Params) -> float:
    """From a pivot to its keyhole's round entry, toward the arm: the screw head goes in there, then pulling the L
    toward the arm seats the shank at the pivot."""
    return p.screw_head_d


def bar_split(p: Params) -> float:
    """Distance from the arm where the bar's end piece joins the corner piece."""
    return p.bed_usable - p.gauge_arm_w / 2 - p.gauge_jig_len - 11.0


def _l_bar(p: Params) -> Sketch:
    """The bar, at the top hole's height, from the arm to past the farthest hook, with the hooks and their notches."""
    top, a, w, r = hole_xs(p)[0], p.gauge_arm_w / 2, p.gauge_pad_w / 2, p.screw_d / 2
    ys = pivot_ys(p)
    y_end = ys[-1] - r - 4.0
    sk = Sketch() + [rect(top - a, top + a, y_end, 0), rect(top - w, top + w, y_end, ys[0] + entry_dy(p) + 9.0)]
    for k, y in enumerate(ys):
        e = y + entry_dy(p)
        sk -= [rect(top - r, top + r, y, e), Pos(top, y) * Circle(r), Pos(top, e) * Circle(p.screw_head_d / 2)]
        sk -= [rect(top + w - 1.0, top + w + 0.01, y - 3.8 - 1.6 * i, y - 3.0 - 1.6 * i) for i in range(k + 1)]
    return sk


def _l_brace(p: Params) -> Sketch:
    """45 degrees from the arm (above the bar) to the bar: keeps the L square."""
    top, w, d = hole_xs(p)[0], p.gauge_brace_w / 2, 60.0
    return poly((top - d - w, 0), (top - d + w, 0), (top + w, -d), (top - w, -d))


def corner_in_gauge(p: Params = P) -> Part:
    """The arm (both pencil holes, the T's socket at its top) with the near half of the bar and a brace."""
    a = p.gauge_arm_w / 2
    s = bar_split(p)
    tab = Pos(hole_xs(p)[0], -s) * Rot(0, 0, -90) * dovetail(0, 0, p.gauge_jig_neck, p.gauge_jig_head, p.gauge_jig_len)
    sk = Sketch() + [rect(p.gauge_split, _length(p), -a, a), _l_brace(p), _l_bar(p) & rect(0, _length(p), -s, a), tab]
    sk -= _tab(p, p.gauge_fit)
    return extrude(sk, p.gauge_t) - _pencil_holes(p)


def bar_end_in_gauge(p: Params = P) -> Part:
    """The far half of the bar, with both hooks."""
    s = bar_split(p)
    sock = Pos(hole_xs(p)[0], -s) * Rot(0, 0, -90) * dovetail(0, 0, p.gauge_jig_neck, p.gauge_jig_head,
                                                               p.gauge_jig_len, p.gauge_fit)
    return extrude((_l_bar(p) & rect(0, _length(p), -1000, -s)) - sock, p.gauge_t)


def l_assembled(p: Params = P) -> Part:
    return t_in_gauge(p) + corner_in_gauge(p) + bar_end_in_gauge(p)


def corner_piece(p: Params = P) -> Part:
    """Print orientation: flat on the bed."""
    return _flat(corner_in_gauge(p))


def bar_end_piece(p: Params = P) -> Part:
    return _flat(bar_end_in_gauge(p))
