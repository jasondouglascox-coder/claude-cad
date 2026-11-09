"""Corner deck for one span, one flat printable part like the straight tie ladder: open ties on two
runners under the rails, a groove sunk in them for each rail's base following the true track curve, gray clips over
the base on every clip_every-th tie, spike heads clear of it on the rest. On the bridge it rests on the two aluminum
rods, which sit in shallow part-circle grooves under the ties (alignment); the inside corners' decks have no grooves.
Its ends sit on the floor beams' V ridges, and its tie ends slide into the side frames' U ledges (glued). Two colors, one change:
brown ties/runners, gray clips on top."""
import math

from build123d import Axis, Circle, Compound, Location, Part, Plane, Polygon, Pos, Rectangle, Rot, Sketch, extrude, revolve

from cadkit.shapes import dovetail
from hotrain.joints import jigsaw, poly, rect
from hotrain.params import P, Params
from hotrain.parts import bow_frame, floor_beam, tie_ladder
from hotrain.span_geom import SpanGeom, end_fractions, frame_x_range, offset_at, span_geom, track_at, track_len


def _clip(g: SpanGeom) -> Sketch:
    """Region between the span's two (shortened) end lines."""
    if not g.curved:
        return rect(g.d, g.s - g.d, -200, 200)
    f0, f1 = end_fractions(g)
    cx, cy = g.s / 2, g.h
    pts = [(cx, cy)]
    for i in range(13):
        f = f0 + (f1 - f0) * i / 12
        x, y, _ = track_at(g, f)
        k = 1.6  # well past the outer edge beam
        pts.append((cx + k * (x - cx), cy + k * (y - cy)))
    return poly(*pts)


def _band(g: SpanGeom, p: Params) -> Sketch:
    """Ties end at the frames' inner faces (less the frame fit), inside the frames' U ledges."""
    lim = p.bow_frame_y - p.bow_frame_t / 2 - p.fit_frame
    return rect(-50, g.s + 50, g.yc - lim, g.yc + lim)


def _oriented_rect(cx: float, cy: float, a: float, along: float, across: float, off_u: float = 0.0) -> Sketch:
    """Rectangle centered u = off_u to the left of (cx, cy), long side 'across' the track direction a."""
    return Pos(cx - off_u * math.sin(a), cy + off_u * math.cos(a)) * Rot(0, 0, math.degrees(a)) * Rectangle(along, across)


def _along(p: Params, g: SpanGeom, u: float, face_at) -> Part:
    """Sweep a cross-section face_at(r_or_y) along the line u left of the track over the span."""
    f0, f1 = end_fractions(g)
    if not g.curved:
        return Pos(g.d, 0, 0) * extrude(Plane.YZ * face_at(u), g.s - 2 * g.d)
    t0 = -g.alpha / 2 + f0 * g.alpha
    part = revolve(Plane.XZ * face_at(g.r - u), Axis.Z, math.degrees((f1 - f0) * g.alpha))
    return Pos(g.s / 2, g.h, 0) * Rot(0, 0, math.degrees(t0) - 90) * part


def _rail_runner(p: Params, g: SpanGeom, u: float) -> Part:
    """Brown strip under a rail, tie level, joining the ties (like the straight ladder's runners)."""
    return _along(p, g, u, lambda c: Pos(c, p.tie_h / 2) * Rectangle(p.runner_w, p.tie_h))


def _rail_groove(p: Params, g: SpanGeom, u: float) -> Part:
    """The rail base's groove along a rail, rail_sink deep from the tie tops (cut from the ties and runners)."""
    return _along(p, g, u, lambda c: Pos(c, p.rail_base_z + (p.rail_sink + 1) / 2) * Rectangle(p.groove_w,
                                                                                               p.rail_sink + 1))


def _rod_groove(p: Params, g: SpanGeom, u: float) -> Part:
    """Rod-sized cylinder along the rod's true path: cut from the ties it leaves a shallow groove."""
    return _along(p, g, u, lambda c: Pos(c, p.rod_zc) * Circle((p.rod_d + p.fit_slide) / 2))


def _at_portal(p: Params, g: SpanGeom, f: float, u: float, back: bool = False) -> Location:
    """At the portal end f (0 or 1), u left of the track, x pointing along the track (back: the other way)."""
    x, y, a = track_at(g, f)
    return Pos(*offset_at(g, f, u)) * Rot(0, 0, math.degrees(a) + (180 if back else 0))


def _stub(p: Params, g: SpanGeom, f: float, u: float, gap: float = 0.0) -> Sketch:
    """A runner from gap short of the portal into the span, over the floor beam: its runner's end."""
    ln = g.d + 0.5 - gap
    return _at_portal(p, g, f, u, back=f == 1) * Pos(gap + ln / 2, 0) * Rectangle(ln, p.runner_w)


def _stub_groove(p: Params, g: SpanGeom, f: float, u: float) -> Sketch:
    """The rail groove on through a stub, from a hair past the portal."""
    return _at_portal(p, g, f, u, back=f == 1) * Pos((g.d + 2) / 2 - 1, 0) * Rectangle(g.d + 2, p.groove_w)


def _dovetail(p: Params, gap: float, clearance: float = 0.0) -> Sketch:
    """The jigsaw tab across a portal, from gap short of it (the tab deck's stub end) jig_len past it."""
    return dovetail(-gap, 0, p.jig_neck, p.jig_head, p.jig_len + gap, clearance)


def _socket(p: Params, g: SpanGeom, f: float, u: float, gap: float = 0.0) -> Sketch:
    """The socket in a stub for a tab coming in across the portal (gap 0: a run ladder's tab), fit_jig all round: no
    slack along the track either (2026-11-08: the room past the tab's tip let the decks shuffle)."""
    if not gap:
        return _at_portal(p, g, f, u, back=f == 1) * jigsaw(p, 0, 0, p.fit_jig)
    return _at_portal(p, g, f, u, back=f == 1) * _dovetail(p, gap, p.fit_jig)


def _tab(p: Params, g: SpanGeom, f: float, u: float, gap: float) -> Sketch:
    """A tab out across the portal into the next deck's socket, from this deck's stub end."""
    return _at_portal(p, g, f, u, back=f == 0) * _dovetail(p, gap)


def pad_end(p: Params, rods: bool) -> float:
    """How far past the portal a deck's pad reaches: over the seat and its notch's room (where the first gap starts,
    which a rodless seat's tab rises into)."""
    return floor_beam.seat_half(p, rods) + p.deck_notch_room + 0.5


def _pad(p: Params, g: SpanGeom, f: float, gap: float, rods: bool) -> Sketch:
    """Between the runners (into them a little, clear of the rail grooves) from gap short of the portal on over the
    floor beam under it: the notch's roof."""
    ln = pad_end(p, rods) - gap
    return _at_portal(p, g, f, 0, back=f == 1) * Pos(gap + ln / 2, 0) * Rectangle(ln, p.rail_ctc - p.runner_w + 1)


def _notch(p: Params, g: SpanGeom, f: float, rods: bool) -> Part:
    """The V notch over the beam's ridge, fit_ridge off its flanks, from past the deck's end to deck_notch_room past
    the beam, so it locates the deck across the track only (45-degree roofs: no bridge on the bed side)."""
    a = p.fb_ridge_h + p.fit_ridge * math.sqrt(2)
    ln = floor_beam.seat_half(p, rods) + p.deck_notch_room + 1
    v = extrude(Plane.YZ * poly((-(a + 1), -1), (a + 1, -1), (0, a)), ln)
    return _at_portal(p, g, f, 0, back=f == 1) * Pos(-1, 0, 0) * v


def ends(end) -> tuple[str, str]:
    """What each end of a deck has: "run" (sockets for a run ladder's tabs), "socket" or "tab". Decks lock in order
    from P0, each tab into the next deck's socket. end: "" (a plain span), "in" (P0's end span) or "out" (the last
    one, turned round: its x = 0 end at the exit anchor)."""
    if end in (True, "in"):
        return "run", "tab"
    if end == "out":
        return "run", "socket"
    return "socket", "tab"


def tie_fracs(p: Params, g: SpanGeom) -> list[float]:
    f0, f1 = end_fractions(g)
    n = max(1, round((f1 - f0) * track_len(g) / p.tie_pitch))
    return [f0 + (f1 - f0) * (k + 0.5) / n for k in range(n)]


def bodies(p: Params, curved: bool, end: str | bool = "", rods: bool = True) -> dict[str, Part]:
    """Deck in the span frame as two print colors: "wood" (ties + rod runners, one connected piece, all at or
    below the tie tops) and "steel" (the rail clips, all above): one color change.
    Its runners reach both portals, over the floor beams, with a jigsaw socket at one end and a tab at the other, so
    the decks lock together (the user, 2026-11-07). end: "in" or "out", a corner's first or (turned round) last
    straight span, where a run meets it: sockets at the anchor for the run deck's tabs (see `ends`).
    Over each floor beam a pad between the runners has a V notch under it that sits on the beam's ridge (2026-11-08).
    rods=False (inside corners): no rod grooves under the ties (they failed prints)."""
    if end and curved:
        raise ValueError("a corner's end spans are straight")
    g = span_geom(p, curved)
    clip, band = _clip(g), _band(g, p)
    across = 2 * p.bow_frame_y
    base = []
    for f in tie_fracs(p, g):
        x, y, a = track_at(g, f)
        base.append(_oriented_rect(x, y, a, p.tie_w, across))
    ties = (Sketch() + base) & band & clip
    wood = extrude(ties, p.tie_h)
    for u in (p.rail_ctc / 2, -p.rail_ctc / 2):
        wood += _rail_runner(p, g, u)
    for u in (p.rod_y, -p.rod_y) if rods else ():
        wood -= _rod_groove(p, g, u)
    for u in (p.rail_ctc / 2, -p.rail_ctc / 2):
        wood -= _rail_groove(p, g, u)
    for f, kind in zip((0.0, 1.0), ends(end)):  # every deck's runners reach both its portals, over the floor beams
        gap = 0.0 if kind == "run" else p.portal_gap / 2  # between decks: slack, so each drops in between two
        wood += extrude(Sketch() + [_stub(p, g, f, u, gap) for u in p.rail_ys], p.tie_h)
        if kind != "run":  # over a floor beam (a run end sits on the anchor)
            wood += extrude(_pad(p, g, f, gap, rods), p.tie_h)
            wood -= _notch(p, g, f, rods)
        wood -= Pos(0, 0, p.rail_base_z) * extrude(Sketch() + [_stub_groove(p, g, f, u) for u in p.rail_ys],
                                                   p.rail_sink + 1)
        if kind == "tab":  # flat at the groove floor, like the run ladders' tabs: the rail slides over it
            wood += extrude(Sketch() + [_tab(p, g, f, u, gap) for u in p.rail_ys], p.rail_base_z)
        else:
            wood -= extrude(Sketch() + [_socket(p, g, f, u, gap) for u in p.rail_ys], p.tie_h)
    wood = Part(wood.solids())
    gw, clips = p.groove_w / 2, []
    for k, f in enumerate(tie_fracs(p, g)):
        x, y, a = track_at(g, f)
        at = Pos(x, y, p.tie_h) * Rot(0, 0, math.degrees(a))
        for rail in (p.rail_ctc / 2, -p.rail_ctc / 2):
            for s in (1, -1):
                if k % p.clip_every == 0:
                    clips.append(at * Pos(-p.clip_len / 2, 0, 0) * tie_ladder._clip(p, rail + s * gw, s))
                else:
                    clips.append(at * Pos(-p.spike_len / 2, 0, 0) * tie_ladder._spike(p, rail, s))
    steel = Part(Compound(children=clips).solids())
    return {"wood": wood, "steel": steel}


def build(p: Params, curved: bool, end: str | bool = "", rods: bool = True) -> Part:
    """Deck in the span frame (both colors fused)."""
    b = bodies(p, curved, end, rods)
    return b["wood"] + b["steel"]





def make(p: Params = P, curved: bool = True, end: str | bool = "", rods: bool = True) -> Part:
    """Print orientation: tie undersides on the bed (rod grooves and beam notches face the bed), tie plates up."""
    d = build(p, curved, end, rods)
    bb = d.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * d


def painted(p: Params, curved: bool, end: str | bool = "", rods: bool = True) -> Part:
    """The deck as ONE solid in the span frame (CAD/assemblies), tie plates painted gray."""
    from cadkit import paint
    from hotrain.room import IRON, TIE_BROWN
    b = bodies(p, curved, end, rods)
    d = paint.painted(b["wood"], TIE_BROWN, b["steel"], IRON)
    d.label = f"corner_deck_{_kind(curved, end)}"
    return d


def _kind(curved: bool, end: str | bool) -> str:
    if end:
        return "end_out" if end == "out" else "end_in"
    return "curve" if curved else "straight"


def make_colored(p: Params = P, curved: bool = True, end: str | bool = "", rods: bool = True) -> Compound:
    """Print orientation like make(), as wood + steel bodies for a multi-color printer."""
    from hotrain.room import IRON, TIE_BROWN
    kind = _kind(curved, end)
    b = bodies(p, curved, end, rods)
    bb = (b["wood"] + b["steel"]).bounding_box()
    out = []
    for name, col in (("wood", TIE_BROWN), ("steel", IRON)):
        part = Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * b[name]
        part.label, part.color = f"corner_deck_{kind}_{name}", col
        out.append(part)
    return Compound(children=out, label=f"corner_deck_{kind}")


def print_offset(p: Params, curved: bool) -> tuple[float, float, float]:
    bb = build(p, curved).bounding_box()
    return bb.min.X, bb.min.Y, bb.min.Z
