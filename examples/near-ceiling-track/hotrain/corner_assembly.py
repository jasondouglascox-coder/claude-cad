"""Every part of one corner placed in the corner frame (see corner_layout), plus the rods (where it has them),
for review and clash checks."""
import math

from build123d import Align, Axis, Box, Circle, Cylinder, Location, Part, Plane, Pos, Rot, Compound, extrude, revolve

from hotrain import corner_layout as C
from hotrain.params import P, Params
from hotrain.parts import bow_deck, bow_frame, ceiling_anchor, deep_bracket, floor_beam, portal_bracket, rod_anchor
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


def beam_key(p: Params, c: C.Corner, i: int) -> float:
    """The angle its deep bracket's plate crosses portal i's floor beam at (off square)."""
    wall = dict(c.deep)[i]
    h = C.portals(p, c)[i].heading
    return h if wall == "A" else 90 - h


def seat_grooves(p: Params, c: C.Corner) -> Part:
    """Where the trusses' skirts drop into the seats' tops (rodless corners, 2026-11-08), in the corner frame: along
    each frame's line from its span's portal to the next, fit_tab wider than its web each side, from the skirt's
    bottom up past the beam top."""
    t, zb, f = p.bow_frame_t, bow_frame.u_bottom(p), p.fit_tab
    ps, out = C.portals(p, c), []
    for sp in C.spans(p, c):
        a, b = ps[sp.index], ps[sp.index + 1]
        between = (Pos(a.x, a.y, 0) * Rot(0, 0, a.heading) * Box(400, 400, 40, align=(Align.MIN, Align.CENTER, Align.CENTER))
                   & Pos(b.x, b.y, 0) * Rot(0, 0, b.heading) * Box(400, 400, 40, align=(Align.MAX, Align.CENTER, Align.CENTER)))
        for _, yl, xs, ln in frame_lines(p, sp.curved):
            web = Pos(-20, 0, -f) * Box(ln + 40, -zb + 1, t + 2 * f, align=(Align.MIN, Align.MIN, Align.MIN))
            out.append(span_location(sp) * frame_location(p, sp.curved, yl, xs, ln) * web & between)
    return Part(Compound(children=out).solids())


def supports(p: Params, c: C.Corner) -> list[tuple[int, str, Part, Location]]:
    """(portal index, name, print-orientation part, its location in the corner) of the floor beam or portal bracket
    under each portal between the anchors; rodless, each with the grooves its trusses' skirts sit in. A portal
    bracket's grooves step where the straight span's trusses meet the curve's, so P1's and the last one's differ."""
    ps, walls, out = C.portals(p, c), dict(c.portal), []
    grooves = None if c.rods else seat_grooves(p, c)
    for i, pt in enumerate(ps[1:-1], start=1):
        if i not in walls:
            key = None if c.rods else beam_key(p, c, i)  # rodless: keyed to its deep bracket
            part = floor_beam.make(p, rods=c.rods, key_deg=key)
            name = "floor_beam" if c.rods else f"floor_beam_seat_{key:.0f}"
            loc = floor_beam.place(p, pt.x, pt.y, pt.heading, rods=c.rods, key_deg=key)
        else:
            part = portal_bracket.make(p)
            name = "portal_bracket" if i == 1 else "portal_bracket_out"
            loc = portal_bracket.place(p, pt.x) if walls[i] == "A" else (wall_b_frame(p, c)
                                                                         * portal_bracket.place(p, pt.y))
        if grooves is not None:
            part = Part((part - loc.inverse() * grooves).solids())
        part.label = name
        out.append((i, name, part, loc))
    return out


def placed_parts(p: Params = P, c: C.Corner = C.inside_corner()) -> list[tuple[str, Part]]:
    out = []
    decks = {cv: bow_deck.painted(p, cv, rods=c.rods) for cv in (False, True)}  # one each, tie plates painted gray
    end_in, end_out = (bow_deck.painted(p, False, end=e, rods=c.rods) for e in ("in", "out"))  # where a run meets the corner
    spans = C.spans(p, c)
    for sp in spans:
        loc = span_location(sp)
        if sp == spans[0]:
            out.append((f"deck{sp.index}", loc * end_in))
        elif sp == spans[-1]:  # turned round: its run sockets at the exit portal
            out.append((f"deck{sp.index}", loc * Pos(span_geom(p, False).s, 0, 0) * Rot(0, 0, 180) * end_out))
        else:
            out.append((f"deck{sp.index}", loc * decks[sp.curved]))
        for kind, yl, xs, ln in frame_lines(p, sp.curved):
            fr = bow_frame.make(p, ln)
            fr.label = f"corner_frame_{kind}"
            side = "inner" if yl > span_geom(p, sp.curved).yc else "outer"
            out.append((f"frame{sp.index}_{side}", loc * frame_location(p, sp.curved, yl, xs, ln) * fr))
    ps = C.portals(p, c)
    for i, name, part, loc in supports(p, c):
        out.append((f"{'portal' if name.startswith('portal') else 'floor_beam'}{i}", loc * part))
    anchor = ceiling_anchor.make(p)
    anchor.label = "ceiling_anchor"
    for i in c.ceiling:
        for s in (1, -1):
            x, y = C.line_point(p, ps[i], s)
            out.append((f"ceiling_anchor{i}_{s}", ceiling_anchor.place(p, x, y) * anchor))
    anc = rod_anchor.make(p)
    anc.label = "rod_anchor"
    out.append(("anchor_in", rod_anchor.place(p, 0) * anc))
    anc_out = anc if c.wall_b else rod_anchor.make(p, bump_out=True)  # the bridge ends at the bump-out's corner
    anc_out.label = "rod_anchor"
    out.append(("anchor_out", wall_b_frame(p, c) * rod_anchor.place(p, ps[-1].y) * anc_out))
    xb = C.curve_start_x(p, c) + p.curve_r + p.track_offset
    for i, wall in c.deep:
        pt = ps[i]
        if wall == "A":
            db = deep_bracket.make(p, pt.y + p.track_offset, pt.heading, c.rods)
            db.label = "deep_bracket"
            out.append((f"deep{i}", deep_bracket.place(p, pt.x) * db))
        else:
            db = deep_bracket.make(p, xb - pt.x, 90 - pt.heading, c.rods)
            db.label = "deep_bracket"
            out.append((f"deep{i}", wall_b_frame(p, c) * deep_bracket.place(p, pt.y) * db))
    for u, side in ((p.rod_y, "inner"), (-p.rod_y, "outer")) if c.rods else ():
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


def _flat(p: Params, c: C.Corner, i: int) -> float:
    """How far from portal i toward its end anchor the bus stays at that portal's height: past the part under it and
    any wall flange on that side. Flanges run along +x of their bracket frame: at P0 (and wall A) into the corner,
    on wall B out of it, toward the exit anchor."""
    n = len(C.portals(p, c)) - 1
    if i in (0, n):
        return p.flange_w - p.bracket_t / 2 + 1 if i == 0 else p.bracket_t / 2 + 1
    t = floor_beam.thickness(p, c.rods)
    flange_toward_anchor = i == n - 1 and dict(c.portal).get(i) == "B"
    return p.flange_w - t / 2 + 1 if flange_toward_anchor else t / 2 + 1


def bus_points(p: Params, c: C.Corner) -> list[tuple[float, float, float]]:
    """Centers of the bus bundle: in each end anchor's wire notch (where the straight runs carry it), then on each
    floor beam's top just outside the wall-side frames. Next to an anchor it stays level past whatever is under it
    (the beam, a wall flange) and climbs or drops the 4 mm in the open span."""
    ps = C.portals(p, c)
    n = len(ps) - 1
    notch = -(p.track_offset - p.flange_t - 0.5 - p.bus_w / 2)  # against the notch's wall end, as on the runs
    out = []
    for i, pt in enumerate(ps):
        end = i in (0, n)
        u, z = (notch, p.bus_floor + p.bus_h / 2) if end else (floor_beam.bus_u(p), floor_beam.bus_z(p))
        x, y = floor_beam.plan(p, pt, u)
        here = [(x, y, z)]
        toward = 1 if i in (0, n - 1) else -1 if i in (1, n) else 0  # along the heading toward the anchor's span
        if toward:
            a, k = math.radians(pt.heading), _flat(p, c, i) * toward
            more = (x + k * math.cos(a), y + k * math.sin(a), z)
            here = here + [more] if toward > 0 else [more] + here
        out += here
    return out


def bus(p: Params, c: C.Corner) -> list[tuple[str, Part]]:
    """Two 16 AWG wires (bus_w x bus_h bundle), straight from notch to beam top to beam top to notch."""
    pts = bus_points(p, c)
    out = []
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        run = math.hypot(dx, dy)
        hd, pitch = math.degrees(math.atan2(dy, dx)), math.degrees(math.atan2(dz, run))
        out.append((f"bus{k}", Pos(*a) * Rot(0, 0, hd) * Rot(0, -pitch, 0)
                    * Box(math.hypot(run, dz), p.bus_w, p.bus_h, align=(Align.MIN, Align.CENTER, Align.CENTER))))
    return out


def make(p: Params = P, c: C.Corner = C.inside_corner()) -> Compound:
    return Compound(children=[s for _, s in placed_parts(p, c)], label=f"{c.name}_corner")
