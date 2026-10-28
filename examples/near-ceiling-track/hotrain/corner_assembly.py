"""Every part of one corner placed in the corner frame (see corner_layout), plus the rods,
for review and clash checks."""
import math

from build123d import Align, Axis, Box, Circle, Cylinder, Location, Part, Plane, Pos, Rot, Compound, extrude, revolve

from hotrain import corner_layout as C
from hotrain.params import P, Params
from hotrain.parts import bow_deck, bow_frame, ceiling_anchor, deep_bracket, floor_beam, rod_anchor
from hotrain.span_geom import frame_x_range, span_geom


def wall_b_frame(p: Params, c: C.Corner) -> Location:
    """Maps a wall-A style frame (track along +x, wall at y = -o) onto the exit straight / wall B."""
    xb = C.curve_start_x(p, c) + p.curve_r
    return Pos(xb, 0, 0) * Rot(0, 0, 90)


def span_location(sp: C.Span) -> Location:
    hd = math.degrees(math.atan2(sp.b.y - sp.a.y, sp.b.x - sp.a.x))
    return Pos(sp.a.x, sp.a.y, 0) * Rot(0, 0, hd)


def frame_location(p: Params, curved: bool, yl: float, xs: float, ln: float = 0.0) -> Location:
    """Print frame -> span frame: outer face outward, the U ledges facing the track, bottom at u_bottom."""
    t, zb = p.bow_frame_t, bow_frame.u_bottom(p)
    if yl > span_geom(p, curved).yc:  # print Z (inward) -> -Y
        return Pos(xs, yl + t / 2, zb) * Rot(90, 0, 0)
    return Pos(xs + ln, yl - t / 2, zb) * Rot(0, 0, 180) * Rot(90, 0, 0)  # print Z -> +Y


def frame_lines(p: Params, curved: bool) -> list[tuple[str, float, float, float]]:
    """(kind, y line, x start, length) for the two frames of a span, in the span frame."""
    g = span_geom(p, curved)
    out = []
    for sgn, side in ((1, "inner"), (-1, "outer")):
        yl = g.yc + sgn * p.bow_frame_y
        xa, xb = frame_x_range(g, yl)
        kind = side if curved else "straight"
        out.append((kind, yl, xa + p.portal_gap, xb - xa - 2 * p.portal_gap))
    return out


def rod(p: Params, c: C.Corner, u: float) -> Part:
    """Rod u to the left of the track, from rod_tail before P0 to rod_tail past the last portal."""
    r_disc = (p.rod_d) / 2
    x1, r = C.curve_start_x(p, c), p.curve_r
    parts = [Pos(-p.rod_tail, u, p.rod_zc) * extrude(Plane.YZ * Circle(r_disc), x1 + p.rod_tail)]
    face = Plane.XZ * (Pos(r - u, p.rod_zc) * Circle(r_disc))
    parts.append(Pos(x1, r, 0) * Rot(0, 0, -90) * revolve(face, Axis.Z, 90))
    ln = c.n_out * p.bow_span + p.rod_tail
    parts.append(Pos(x1 + r - u, r, p.rod_zc) * extrude(Plane.XZ * Circle(r_disc), -ln))
    out = parts[0]
    for q in parts[1:]:
        out += q
    return out


def placed_parts(p: Params = P, c: C.Corner = C.inside_corner()) -> list[tuple[str, Part]]:
    out = []
    decks = {cv: bow_deck.painted(p, cv) for cv in (False, True)}  # one part each, gray tie plates painted on
    end = bow_deck.painted(p, False, end=True)  # where a run meets the corner: sockets at the portal
    spans = C.spans(p, c)
    for sp in spans:
        loc = span_location(sp)
        if sp == spans[0]:
            out.append((f"deck{sp.index}", loc * end))
        elif sp == spans[-1]:  # turned round: its sockets at the exit portal
            out.append((f"deck{sp.index}", loc * Pos(span_geom(p, False).s, 0, 0) * Rot(0, 0, 180) * end))
        else:
            out.append((f"deck{sp.index}", loc * decks[sp.curved]))
        for kind, yl, xs, ln in frame_lines(p, sp.curved):
            fr = bow_frame.make(p, ln)
            fr.label = f"corner_frame_{kind}"
            side = "inner" if yl > span_geom(p, sp.curved).yc else "outer"
            out.append((f"frame{sp.index}_{side}", loc * frame_location(p, sp.curved, yl, xs, ln) * fr))
    ps = C.portals(p, c)
    beams = {False: floor_beam.make(p, False), True: floor_beam.make(p, True)}
    beams[False].label, beams[True].label = "floor_beam", "floor_beam_drop"  # drop variant no longer used
    for i, pt in enumerate(ps[1:-1], start=1):
        out.append((f"floor_beam{i}", floor_beam.place(p, pt.x, pt.y, pt.heading) * beams[False]))
    anchor = ceiling_anchor.make(p)
    anchor.label = "ceiling_anchor"
    for i in c.ceiling:
        for s in (1, -1):
            x, y = C.line_point(p, ps[i], s)
            out.append((f"ceiling_anchor{i}_{s}", ceiling_anchor.place(p, x, y) * anchor))
    anc = rod_anchor.make(p)
    anc.label = "rod_anchor"
    out.append(("anchor_in", rod_anchor.place(p, 0) * anc))
    out.append(("anchor_out", wall_b_frame(p, c) * rod_anchor.place(p, ps[-1].y) * anc))
    xb = C.curve_start_x(p, c) + p.curve_r + p.track_offset
    for i, wall in c.deep:
        pt = ps[i]
        if wall == "A":
            db = deep_bracket.make(p, pt.y + p.track_offset, pt.heading)
            db.label = "deep_bracket"
            out.append((f"deep{i}", deep_bracket.place(p, pt.x) * db))
        else:
            db = deep_bracket.make(p, xb - pt.x, 90 - pt.heading)
            db.label = "deep_bracket"
            out.append((f"deep{i}", wall_b_frame(p, c) * deep_bracket.place(p, pt.y) * db))
    for u, side in ((p.rod_y, "inner"), (-p.rod_y, "outer")):
        r = rod(p, c, u)
        r.label = f"aluminum_rod_{side}"
        out.append((f"rod_{side}", r))
    return out


def cables(p: Params, c: C.Corner) -> list[tuple[str, Part]]:
    """Hanging lines (50 lb braid) from the top of the wrapped tie ends up to each ceiling anchor."""
    out = []
    top = p.rail_top + p.rail_top_below_ceiling - ceiling_anchor.height(p)
    for i in c.ceiling:
        for s in (1, -1):
            x, y = C.line_point(p, C.portals(p, c)[i], s)
            out.append((f"line{i}_{s}", Pos(x, y, p.tie_h) * Cylinder(p.line_d / 2, top - p.tie_h,
                                                                     align=(Align.CENTER, Align.CENTER, Align.MIN))))
    return out


def bus(p: Params, c: C.Corner) -> list[tuple[str, Part]]:
    """Two 16 AWG wires (4.8 x 2.4 mm bundle) resting in the floor-beam hooks, straight between hooks."""
    ps = C.portals(p, c)[1:-1]
    hb, zc = floor_beam.bus_u(p), floor_beam.bus_z(p)
    pts = []
    for pt in ps:
        a = math.radians(pt.heading)
        pts.append((pt.x - hb * math.sin(a), pt.y + hb * math.cos(a)))
    out = []
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        ln = math.dist(a, b)
        hd = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        out.append((f"bus{k}", Pos(a[0], a[1], zc) * Rot(0, 0, hd)
                    * Box(ln, 4.8, 2.4, align=(Align.MIN, Align.CENTER, Align.CENTER))))
    return out


def make(p: Params = P, c: C.Corner = C.inside_corner()) -> Compound:
    return Compound(children=[s for _, s in placed_parts(p, c)], label=f"{c.name}_corner")
