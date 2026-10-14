"""Corner deck for one span, one flat printable part like the straight tie ladder: open ties on two
runners under the rails, gauge-setting tie plates following the true track curve. It rests on the two
aluminum rods, which sit in shallow part-circle grooves under the ties (alignment), and its tie ends slide
into the side frames' U ledges (glued). Two colors, one change: brown ties/runners, gray tie plates on top."""
import math

from build123d import Axis, Circle, Compound, Part, Plane, Polygon, Pos, Rectangle, Rot, Sketch, extrude, revolve

from hotrain.joints import poly, rect
from hotrain.params import P, Params
from hotrain.parts import bow_frame
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
    """Ties end at the frames' inner faces (less the slide fit), inside the frames' U ledges."""
    lim = p.bow_frame_y - p.bow_frame_t / 2 - p.fit_slide
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


def _rod_groove(p: Params, g: SpanGeom, u: float) -> Part:
    """Rod-sized cylinder along the rod's true path: cut from the ties it leaves a shallow groove."""
    return _along(p, g, u, lambda c: Pos(c, p.rod_zc) * Circle((p.rod_d + p.fit_slide) / 2))


def tie_fracs(p: Params, g: SpanGeom) -> list[float]:
    f0, f1 = end_fractions(g)
    n = max(1, round((f1 - f0) * track_len(g) / p.tie_pitch))
    return [f0 + (f1 - f0) * (k + 0.5) / n for k in range(n)]


def bodies(p: Params, curved: bool) -> dict[str, Part]:
    """Deck in the span frame as two print colors: "wood" (ties + rod runners, one connected piece, all at or
    below the tie tops) and "steel" (tie plates, shoulders, spike lips, all above): one color change."""
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
    for u in (p.rod_y, -p.rod_y):
        wood -= _rod_groove(p, g, u)
    wood = Part(wood.solids())
    # tie plates, shoulders, outer spike lips along the true rails
    gw, sw = p.groove_w / 2, p.shoulder_w
    plates, shoulders, lips = [], [], []
    for k, f in enumerate(tie_fracs(p, g)):
        x, y, a = track_at(g, f)
        for rail in (p.rail_ctc / 2, -p.rail_ctc / 2):
            plates.append(_oriented_rect(x, y, a, p.tie_w, 2 * (gw + sw), rail))
            for side in (1, -1):
                shoulders.append(_oriented_rect(x, y, a, p.tie_w, sw, rail + side * (gw + sw / 2)))
            if k % p.spike_lip_every == 0:
                side = 1 if rail > 0 else -1  # outside of the rail only
                lips.append(_oriented_rect(x, y, a, p.tie_w, sw + p.spike_lip_overhang,
                                           rail + side * (gw + sw / 2 - p.spike_lip_overhang / 2)))
    z = p.tie_h
    steel = Pos(0, 0, z) * extrude(Sketch() + plates, p.tie_plate_h)
    z += p.tie_plate_h
    steel += Pos(0, 0, z) * extrude(Sketch() + shoulders, p.shoulder_h)
    z += p.shoulder_h
    if lips:
        steel += Pos(0, 0, z) * extrude(Sketch() + lips, p.spike_lip_t)
    steel = Part(steel.solids())
    return {"wood": wood, "steel": steel}


def build(p: Params, curved: bool) -> Part:
    """Deck in the span frame (both colors fused)."""
    b = bodies(p, curved)
    return b["wood"] + b["steel"]





def make(p: Params = P, curved: bool = True) -> Part:
    """Print orientation: tie undersides on the bed (rod grooves face the bed), tie plates up."""
    d = build(p, curved)
    bb = d.bounding_box()
    return Pos(-bb.min.X, -bb.min.Y, -bb.min.Z) * d


def painted(p: Params, curved: bool) -> Part:
    """The deck as ONE solid in the span frame (CAD/assemblies), tie plates painted gray."""
    from hotrain import paint
    from hotrain.room import IRON, TIE_BROWN
    b = bodies(p, curved)
    d = paint.painted(b["wood"], TIE_BROWN, b["steel"], IRON)
    d.label = f"corner_deck_{'curve' if curved else 'straight'}"
    return d


def make_colored(p: Params = P, curved: bool = True) -> Compound:
    """Print orientation like make(), as wood + steel bodies for a multi-color printer."""
    from hotrain.room import IRON, TIE_BROWN
    kind = "curve" if curved else "straight"
    b = bodies(p, curved)
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
