"""Ceiling gauge: a thin T held against the ceiling, with a pencil hole at each bracket screw line, so every
bracket and rod anchor is marked at the same height round the room. Gauge frame: x down from the ceiling (the T's
top edge at x = 0), y across, z out of the wall. Longer than the bed, so it prints as the T (bar, braces, a stub)
and the arm (both holes), joined by a glued dovetail at x = gauge_split."""
from build123d import Circle, Part, Pos, Rot, Sketch, extrude

from cadkit.shapes import dovetail
from hotrain.joints import poly, rect
from hotrain.params import P, Params


def hole_xs(p: Params) -> list[float]:
    """Top and bottom screw centers below the ceiling."""
    return [p.screw_below_ceiling, p.screw_below_ceiling + p.screw_zs[1] - p.screw_zs[0]]


def _length(p: Params) -> float:
    return hole_xs(p)[-1] + p.gauge_tail


def _tab(p: Params, clearance: float = 0.0) -> Sketch:
    return dovetail(p.gauge_split, 0, p.gauge_jig_neck, p.gauge_jig_head, p.gauge_jig_len, clearance)


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
    sk = rect(p.gauge_split, _length(p), -a, a) - _tab(p, p.fit_snap)
    sk -= [Pos(x, 0) * Circle(p.gauge_hole_d / 2) for x in hole_xs(p)]
    return extrude(sk, p.gauge_t)


def assembled(p: Params = P) -> Part:
    return t_in_gauge(p) + arm_in_gauge(p)


def _flat(part: Part) -> Part:
    bb = part.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, 0) * part


def t_piece(p: Params = P) -> Part:
    """Print orientation: flat on the bed."""
    return _flat(t_in_gauge(p))


def arm_piece(p: Params = P) -> Part:
    return _flat(arm_in_gauge(p))
