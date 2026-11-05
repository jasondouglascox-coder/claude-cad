"""Open bridge-tie ladder: ties on two hidden runners, a groove sunk in them for each rail's base (it presses in),
gray clips over the base both sides on every clip_every-th tie (it snaps under them), gray spike heads clear of it on
the ties between, long ties.
At each bay's mid is a solder gap for feeders, which solder to the OUTSIDE of the rail (the gauge side must
stay clear for deep vintage flanges): over the gap, each runner is notched from the rail groove's outer
edge outward, and the gap ties keep only their center part between the rails. The runners' inner parts
stay continuous and carry the rail. On the room side the gap ties keep a short end stub (held by a low,
set-back bar on top, flush with the tie tops) so the tie line still reads from the room. In the gap's first
opening a feeder groove runs straight across under both rails, over a thin floor, so the room rail's feeder
ducks under both rails to the wall side and the rest of the gap is free to bend the wire and solder.
A tie over a panel tab's slot gets no clip or spike (it would bridge the slot), so the slot is open to the sky."""
from build123d import Align, Box, Compound, Cylinder, Location, Part, Plane, Pos, Rot, Sketch, extrude

from hotrain import layout as L
from hotrain.joints import jigsaw, poly, rect
from hotrain.params import P, Params


def bodies(p: Params, ties: list, x_start: float, x_end: float, tab_xs: list[float],
           female_start: bool, male_end: bool, rod_spans: list = (), male_start: bool = False) -> dict[str, Part]:
    """Ladder in the run frame (x along track, y across, z = 0 at tie underside) as two print colors:
    "wood" (ties, runners, jigsaw tabs, the rail grooves; one piece, up to the tie tops) and "steel" (the rail
    clips, all above): one color change."""
    gaps = [t for t in ties if x_start < t.x < x_end and t.gap]
    ts = [t for t in ties if x_start < t.x < x_end and not t.gap]
    hw, g = p.tie_w / 2, p.groove_w / 2
    base = []
    for t in ts:
        base.append(rect(t.x - hw, t.x + hw, -p.tie_l / 2, p.long_tie_reach if t.long else p.tie_l / 2))
        if t.long:
            base.append(rect(max(t.x - p.socket_pad / 2, x_start), min(t.x + p.socket_pad / 2, x_end),
                             p.handrail_offset - p.socket_pad / 2, p.handrail_offset + p.socket_pad / 2))
    end, stub = p.tie_l / 2, p.solder_room_stub
    for t in gaps:  # center part between the rails, and room-side fake tie ends
        base.append(rect(t.x - hw, t.x + hw, -p.rail_ctc / 2, p.rail_ctc / 2))
        base.append(rect(t.x - hw, t.x + hw, end - stub, end))
    bars = []
    if gaps:
        pitch = min(abs(a.x - b.x) for a, b in zip(ties, ties[1:]))
        bx0 = max(min(t.x for t in gaps) - pitch, x_start)
        bx1 = min(max(t.x for t in gaps) + pitch, x_end)
        bars.append(rect(bx0, bx1, end - stub, end - p.solder_bar_inset))
    for y in p.rail_ys:
        base.append(rect(x_start, x_end, y - p.runner_w / 2, y + p.runner_w / 2))
        if male_end:
            base.append(jigsaw(p, x_end, y))
        if male_start:  # a run's corner end: the tab points back out, into the corner's end deck
            base.append(Rot(0, 0, 180) * jigsaw(p, -x_start, -y))
    cuts = []
    if gaps:  # notch each runner from the rail groove's outer edge outward, between the full ties
        pb = min(abs(a.x - b.x) for a, b in zip(ties, ties[1:]))
        nx0, nx1 = min(t.x for t in gaps) - pb + hw, max(t.x for t in gaps) + pb - hw
        for y in p.rail_ys:
            s = 1 if y > 0 else -1
            a, b = y + s * g, y + s * (p.runner_w / 2 + 0.01)
            cuts.append(rect(nx0, nx1, min(a, b), max(a, b)))
    tl, tw = (p.tab_len + p.fit_tab) / 2, (p.panel_t + p.fit_tab) / 2
    for x in tab_xs:
        if x_start + tl < x < x_end - tl:
            cuts += [rect(x - tl, x + tl, y - tw, y + tw) for y in p.rail_ys]
    for t in ts:
        if t.long:
            px, py = (p.peg_w + p.fit_slide) / 2, (p.handrail_t + p.fit_slide) / 2  # slide fit + a drop of glue
            cuts.append(rect(t.x - px, t.x + px, p.handrail_offset - py, p.handrail_offset + py))
    if female_start:
        cuts += [jigsaw(p, x_start, y, p.fit_snap) for y in p.rail_ys]
    footprint = (Sketch() + base) - cuts
    wood = extrude(footprint, p.tie_h)
    if gaps:  # feeder groove across both runners, between the full tie and the first gap tie, over a floor
        pb = min(abs(a.x - b.x) for a, b in zip(ties, ties[1:]))
        xn, yw = min(t.x for t in gaps) - pb / 2, max(p.rail_ys) + p.runner_w / 2 + 0.01
        wood -= Pos(xn, 0, p.solder_feed_floor) * Box(p.solder_feed_w, 2 * yw, p.tie_h,
                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))
    run_out = p.jig_len + 1  # on out through the jigsaw tabs, so no nub of them stands in the rail's path
    for y in p.rail_ys:  # the rail grooves, the length of the ladder
        wood -= Pos(x_start - run_out, y, p.rail_base_z) * Box(x_end - x_start + 2 * run_out, p.groove_w,
                                                             p.rail_sink + 1, align=(Align.MIN, Align.CENTER, Align.MIN))
    if bars:  # on top, flush with the tie tops: hidden from below, reads as a guard timber from above
        wood += Pos(0, 0, p.tie_h - p.solder_bar_h) * extrude(Sketch() + bars, p.solder_bar_h)
    for x0, x1 in rod_spans:  # a corner's rod tails reach under the run's end ties: same shallow grooves
        if x1 > x_start and x0 < x_end:
            for y in (p.rod_y, -p.rod_y):
                wood -= Pos(x0, y, p.rod_zc) * Rot(0, 90, 0) * Cylinder((p.rod_d + p.fit_slide) / 2, x1 - x0,
                                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))

    clips = []
    slots = [x for x in tab_xs if x_start + tl < x < x_end - tl]
    for t in (t for t in ts if all(abs(t.x - x) >= tl + hw for x in slots)):  # over a tab slot: open
        for y in p.rail_ys:
            if t.lip:
                clips += [Pos(t.x - p.clip_len / 2, 0, p.tie_h) * _clip(p, y + s * g, s) for s in (1, -1)]
            else:
                clips += [Pos(t.x - p.spike_len / 2, 0, p.tie_h) * _spike(p, y, s) for s in (1, -1)]
    steel = Part(Compound(children=clips).solids())
    steel &= extrude(footprint, p.tie_h + 10)  # gray only over brown: nothing hangs over a socket or slot
    return {"wood": Part(wood.solids()), "steel": Part(steel.solids())}


def _clip(p: Params, yw: float, s: int) -> Part:
    """A rail clip on the tie top, clip_len long in x from x = 0: its foot clip_back wide outside the groove wall at yw
    (s = +1: the groove is toward -y), reaching clip_reach over the groove, clip_h tall. Its underside rises
    clip_rise from the wall to the tip, so each printed layer overhangs the one below by only part of the reach; the
    tip is clip_tip thick and the top slopes from it up to full height at the wall, a lead-in the base pushes past."""
    yt, yo, h = yw - s * p.clip_reach, yw + s * p.clip_back, p.clip_h
    pts = [(yo, 0), (yw, 0), (yt, p.clip_rise), (yt, p.clip_rise + p.clip_tip), (yw, h), (yo, h)]
    return extrude(Plane.YZ * poly(*pts), p.clip_len)


def _spike(p: Params, y: float, s: int) -> Part:
    """A spike head on the tie top beside the rail at y (s = +1: on its +y side), spike_len long in x from x = 0, clip_h
    tall, standing spike_clear off the base's edge: it looks like a nail and never touches the rail."""
    yi = y + s * (p.rail_base_w / 2 + p.spike_clear)
    yo = yi + s * p.spike_w
    return extrude(Plane.YZ * rect(min(yi, yo), max(yi, yo), 0, p.clip_h), p.spike_len)


def build(p: Params, ties: list, x_start: float, x_end: float, tab_xs: list[float],
          female_start: bool, male_end: bool, rod_spans: list = (), male_start: bool = False) -> Part:
    """Ladder in the run frame, both colors fused."""
    b = bodies(p, ties, x_start, x_end, tab_xs, female_start, male_end, rod_spans, male_start)
    return b["wood"] + b["steel"]


def make(p: Params, bays: list[float], seg: L.Segment, ends: tuple = L.RUN_ENDS) -> Part:
    """Print orientation: ties flat on the bed, X from the ladder's start, Y from the wall-side tie end."""
    run = build(p, L.ties(p, bays, ends), seg.x_start, seg.x_end, L.tab_xs(p, bays), seg.female_start, seg.male_end,
                L.rod_tail_spans(p, bays, ends), seg.male_start)
    return Pos(-seg.x_start, p.tie_l / 2, 0) * run


def place(p: Params, seg: L.Segment) -> Location:
    return Pos(seg.x_start, -p.tie_l / 2, 0)


def painted(p: Params, bays: list[float], seg: L.Segment, ends: tuple = L.RUN_ENDS) -> Part:
    """Print-orientation ladder as ONE solid (CAD/assemblies), tie plates painted gray."""
    from cadkit import paint
    from hotrain.room import IRON, TIE_BROWN
    c = make_colored(p, bays, seg, ends)
    return paint.painted(c.children[0], TIE_BROWN, c.children[1], IRON)


def make_colored(p: Params, bays: list[float], seg: L.Segment, ends: tuple = L.RUN_ENDS) -> Compound:
    """Print orientation like make(), as brown wood + gray steel bodies for a multi-color printer."""
    from hotrain.room import IRON, TIE_BROWN
    b = bodies(p, L.ties(p, bays, ends), seg.x_start, seg.x_end, L.tab_xs(p, bays), seg.female_start, seg.male_end,
               L.rod_tail_spans(p, bays, ends), seg.male_start)
    out = []
    for name, col in (("wood", TIE_BROWN), ("steel", IRON)):
        part = Pos(-seg.x_start, p.tie_l / 2, 0) * b[name]
        part.label, part.color = f"ladder_{name}", col
        out.append(part)
    return Compound(children=out, label="ladder")
