"""Cutters and profiles shared by the block, the clip and the fit test, each in its own local frame.

Marker frame: +Z along the marker from its felt point (z = 0) toward the cap. Profiles: (u, v) = (Y, Z) of the use
frame, extruded along the bar."""
from build123d import Align, Cone, Cylinder, Part, Pos, Sketch

from cadkit.shapes import poly, rect
from sharpie_colorizer.layout import (cone_h, fit_start_l, mouth_l, nose_start_l, shoulder_from_tip,
                                      straight_from_tip)
from sharpie_colorizer.params import P, Params

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def _rod(r: float, z0: float, z1: float) -> Part:
    return Pos(0, 0, z0) * Cylinder(r, z1 - z0, align=UP)


def _cone(r0: float, r1: float, z0: float, z1: float) -> Part:
    return Pos(0, 0, z0) * Cone(r0, r1, z1 - z0, align=UP)


def marker_cavity(p: Params = P, fit_d: float | None = None) -> Part:
    """What a socket cuts: a window for the felt (wide enough for one worn wear_max and pushed in), a bore with
    nose_clear all round the nose, and the Ø fit bore that grips the straight front section, past the mouth."""
    fit_d = fit_d or p.marker_fit_d
    k = p.felt_d / 2 / p.felt_l  # felt taper
    apex = -(p.wear_max + p.felt_clear / k)
    felt = _cone(0, k * (p.felt_l + p.wear_max) + p.felt_clear, apex, p.felt_l + 0.5)
    nose = _rod(p.nose_d / 2 + p.nose_clear, nose_start_l(p), fit_start_l(p) + 0.5)
    fit = _rod(fit_d / 2, fit_start_l(p), mouth_l(p) + 5)
    return Part((felt + nose + fit).solids())


def marker_solid(p: Params = P, reading: str = "long", wear: float = 0.0, with_grip: bool = False,
                 felt: bool = True) -> Part:
    """A Sharpie Fine Point, felt point at z = 0. Worn: the felt is `wear` shorter and everything behind it sits
    `wear` deeper, so the blunt end still touches at z = 0. Without the grip, the straight section inside the
    socket is left out: what's left must not touch plastic."""
    k = p.felt_d / 2 / p.felt_l
    straight, shoulder = straight_from_tip(p, reading), shoulder_from_tip(p, reading)
    nose_end = p.felt_l + p.nose_l
    parts = [_rod(p.nose_d / 2, p.felt_l - (0.1 if felt else 0), nose_end),  # overlaps the felt
             _cone(p.nose_d / 2, p.marker_front_d / 2, nose_end - 0.01, straight + 0.01),
             _rod(p.marker_front_d / 2, straight, shoulder + 0.1),
             _rod(p.marker_body_d / 2, shoulder, shoulder + 100)]
    if felt:
        parts.append(_cone(k * wear, p.felt_d / 2, wear, p.felt_l))
    m = Part(sum(parts[1:], parts[0]).solids())
    if not with_grip:
        m -= _rod(p.marker_front_d / 2 + 0.01, straight, mouth_l(p) + wear + 0.5)
    return Pos(0, 0, -wear) * m


def tube_socket(p: Params = P, fit_d: float | None = None) -> Part:
    """Guide-tube socket from a mouth at z = 0: tube_depth of Ø fit, then 45° down to the channel."""
    fit_d = fit_d or p.tube_fit_d
    return Part((_rod(fit_d / 2, 0, p.tube_depth) +
                 _cone(fit_d / 2, p.channel_d / 2, p.tube_depth, p.tube_depth + cone_h(p))).solids())


def rail_profile(p: Params = P, clearance: float = 0.0, peaked: bool = False) -> Sketch:
    """Dovetail rail, neck on v = 0 widening to the head at v = rail_h (from v = -1, to overlap what it sits on).
    With clearance: the slot, every side moved out by it; peaked adds a 45° roof so the slot prints unsupported."""
    slope = (p.rail_head - p.rail_neck) / 2 / p.rail_h
    grow_u = clearance * (1 + slope ** 2) ** 0.5  # an inclined side moved out by `clearance`, measured along u
    half = lambda v: p.rail_neck / 2 + slope * v + grow_u
    top = p.rail_h + clearance
    pts = [(-half(-1), -1), (half(-1), -1), (half(top), top)]
    if peaked:
        pts.append((0, top + half(top)))
    return poly(*pts, (-half(top), top))


def clip_profile(p: Params = P, hook: float = 2.0, rail_grow: float | None = None) -> Sketch:
    """C around the bar (centered on the origin) with lips reaching `hook` in under its bottom edge, a 45° lead-in
    on each lip's lower inside, and the rail (rail_grow fatter than nominal, for a press fit) on the top web."""
    rail_grow = p.rail_grow if rail_grow is None else rail_grow
    a, b = p.bar_w / 2 + p.clip_clear_w, p.bar_h / 2 + p.clip_clear
    A, t = a + p.clip_t, p.clip_t
    tip = p.bar_w / 2 - hook
    right = poly((a, b), (a, -b), (tip, -b), (tip + t, -b - t), (A, -b - t), (A, b))
    left = poly((-a, b), (-A, b), (-A, -b - t), (-tip - t, -b - t), (-tip, -b), (-a, -b))
    web = rect(-A, A, b - 0.01, b + t)
    rail = Pos(0, b + t) * rail_profile(p, rail_grow)
    return Sketch() + [right, left, web, rail]
