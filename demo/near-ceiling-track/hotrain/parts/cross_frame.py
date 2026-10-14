"""H-frame between the two panels at a post. Slots hold panel spacing; its bar seats in the rib notch."""
import math

from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import poly, rect
from hotrain.params import P, Params


def width(p: Params) -> float:
    return p.rail_ctc + p.panel_t + p.fit_slide + 2 * p.cf_wall


def y_min(p: Params) -> float:
    """Wall-side end of the wire finger: flush with the bracket flange face."""
    return -(p.track_offset - p.flange_t)


def height(p: Params, depth: float) -> float:
    return depth + p.cf_bar


def profile(p: Params, depth: float) -> Sketch:
    """Profile in (y, z); depth = distance from tie underside down to the rib underside at this post."""
    w, sw = width(p), p.panel_t + p.fit_slide
    body = rect(-w / 2, w / 2, -height(p, depth), 0)
    ym, fl = y_min(p), p.bus_floor
    body += [rect(ym, -w / 2 + 0.01, fl - p.finger_h, fl),  # finger: the bus wires lie on it
             rect(ym, ym + p.finger_lip_w, fl - p.finger_h, p.finger_lip_top)]  # lip at the wall end
    slot_bottom = -depth + p.rib_notch
    cuts = [rect(y - sw / 2, y + sw / 2, slot_bottom, 1) for y in p.rail_ys]
    wy = p.rail_ctc / 2 - sw / 2 - p.cf_border
    if -p.cf_border - slot_bottom > 3:
        win = rect(-wy, wy, slot_bottom, -p.cf_border)
        if p.run_style == "deck_truss":  # sway bracing: stacked X's
            n = x_cells(p, depth)
            ch = (-p.cf_border - slot_bottom) / n
            bars = []
            for k in range(n):
                z0 = slot_bottom + k * ch
                bars += [_bar((-wy, z0), (wy, z0 + ch), p.cf_x_w), _bar((-wy, z0 + ch), (wy, z0), p.cf_x_w)]
            win = win - bars
        cuts.append(win)
    return body - cuts


def x_cells(p: Params, depth: float) -> int:
    """Number of stacked X's in the sway-brace window (cells roughly 2:1 tall)."""
    wy = p.rail_ctc / 2 - (p.panel_t + p.fit_slide) / 2 - p.cf_border
    h = -p.cf_border + depth - p.rib_notch
    return max(1, round(h / (4 * wy)))


def _bar(a: tuple[float, float], b: tuple[float, float], w: float) -> Sketch:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ox, oy = -dy / n * w / 2, dx / n * w / 2
    return poly((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), (b[0] - ox, b[1] - oy), (a[0] - ox, a[1] - oy))


def make(p: Params = P, depth: float = 40.0) -> Part:
    return Pos(-y_min(p), height(p, depth), 0) * extrude(profile(p, depth), p.cf_t)


def place(p: Params, x: float, depth: float) -> Location:
    return Pos(x, 0, 0) * Rot(0, 0, 90) * Rot(90, 0, 0) * Pos(y_min(p), -height(p, depth), -p.cf_t / 2)
