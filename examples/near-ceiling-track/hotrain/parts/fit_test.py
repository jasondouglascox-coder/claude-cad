"""Calibration coupon: tie-plate grooves, tab slots and keystone sockets at three clearances, plus a latch,
three corner-deck rod-groove seats, and three deck-truss rivet strips (head sizes around rivet_d).
Variant 1/2/3 = smallest/default/largest clearance, marked with 1/2/3 notches."""
from dataclasses import replace

from build123d import Align, Box, Circle, Compound, Cylinder, Part, Plane, Pos, Rectangle, Rot, Sketch, extrude

from hotrain.joints import butterfly, rect
from hotrain.parts import keystone
from hotrain.layout import Tie
from hotrain.params import P, Params
from hotrain.parts import bracket, tie_ladder

GROOVE_FITS = (0.10, 0.20, 0.30)
SLOT_FITS = (0.10, 0.20, 0.30)
KEY_FITS = (0.0, 0.05, 0.10)
ROD_SEAT_FITS = (0.1, 0.2, 0.3)  # clearance of the corner deck's rod grooves on the 1/4" rods: tighter -> looser
RIVET_SIZES = (0.6, 0.8, 1.0)  # deck-truss rivet head diameters: smaller -> larger (rivet_d is the middle one)
RIVET_STRIP = (40.0, 10.0)  # strip length, width
LATCH_DEPTH = 45.0
LATCH_NOTCH = 1.0  # the coupon's short latch sample keeps a shallow pier notch


def marks(n: int, x: float, y: float) -> list[Sketch]:
    return [rect(x + 1.6 * i, x + 1.6 * i + 0.8, y - 0.01, y + 1.0) for i in range(n)]


def groove_sample(p: Params, fit: float, n: int) -> Part:
    q = replace(p, fit_slide=fit)
    ties = [Tie(2.75 + 5.5 * k, False, k == 1) for k in range(3)]
    lad = Pos(0, q.tie_l / 2, 0) * tie_ladder.build(q, ties, 0, 16.5, [], False, False)
    notches = [rect(t.x - 0.5, t.x + 0.5, -0.01, 1.0) for t in ties[:n]]  # wall-side tie ends
    return lad - extrude(Sketch() + notches, q.tie_h)


def slot_plate(p: Params) -> Part:
    body = rect(0, 3 * 14 + 4, 0, 14)
    cuts = []
    for i, f in enumerate(SLOT_FITS):
        cx, hl, hw = 4 + 14 * i + 5, (p.tab_len + f) / 2, (p.panel_t + f) / 2
        cuts.append(rect(cx - hl, cx + hl, 7 - hw, 7 + hw))
        cuts += marks(i + 1, cx - 3, 0)
    return extrude(body - cuts, p.tie_h)


def tab_strip(p: Params) -> Part:
    return extrude(Sketch() + [rect(0, 30, 0, 10), rect(12, 12 + p.tab_len, 9, 10 + p.tie_h)], p.panel_t)


def key_block(p: Params, fit: float, n: int) -> Part:
    p = keystone.key_params(p)
    w, h = 16.0, p.key_head + 8
    body = rect(0, w, 0, h) - [Pos(w, h / 2) * butterfly(p, fit)] - marks(n, 1.0, 0)
    return extrude(body, p.panel_t)


def key(p: Params) -> Part:
    return keystone.make(p)


def latch_block(p: Params) -> Part:
    """A short deck block with one pier slot and the latch, depth LATCH_DEPTH."""
    sw = bracket.slot_w(p)
    y0, y1 = -sw / 2 - 6, sw / 2 + p.latch_finger_w + p.latch_relief + 4
    cuts, hook = bracket.slots_and_latch(p, -LATCH_DEPTH + LATCH_NOTCH, (0.0,))
    prof = (rect(y0, y1, -LATCH_DEPTH - 4, 0) - cuts) + hook
    return extrude(Pos(-y0, LATCH_DEPTH + 4) * prof, p.bracket_t)


def latch_pier(p: Params) -> Part:
    """Pier stub with the window and bottom notch centered, to snap into latch_block."""
    w, bw = 24.0, (p.bracket_t + p.fit_slide) / 2
    prof = rect(-w / 2, w / 2, -LATCH_DEPTH, 0) - [
        rect(-bw, bw, -LATCH_DEPTH - 1, -LATCH_DEPTH + LATCH_NOTCH),
        rect(-bw, bw, -p.latch_top - p.latch_win_h, -p.latch_top),
    ]
    return extrude(Pos(w / 2, LATCH_DEPTH) * prof, p.panel_t)


def rod_seat_sample(p: Params, fit: float, n: int) -> Part:
    """A 20 mm strip of corner-deck tie with the rod groove underneath (printed groove down, as the deck),
    groove clearance `fit`, n notches on top. Lay it on a rod: it should seat without rocking."""
    w, t = 12.0, p.tie_h
    s = extrude(Pos(10.0, 0) * Rectangle(20.0, w), t)
    s -= Pos(0, 0, p.rod_zc) * Rot(0, 90, 0) * Cylinder((p.rod_d + fit) / 2, 20.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    for i in range(n):
        s -= Pos(2 + 3 * i, -w / 2, t - 0.8) * Box(1.0, w, 1.0, align=(Align.MIN, Align.MIN, Align.MIN))
    return Pos(0, w / 2, 0) * Part(s.solids())


def rivet_count(p: Params) -> int:
    """Heads per row on a strip, at the trusses' pitch."""
    return int((RIVET_STRIP[0] - 6.0) // p.rivet_pitch) + 1


def rivet_strip(p: Params, d: float, n: int) -> Part:
    """A strip of truss panel (panel_t thick) with two rows of d mm heads at rivet_pitch, rivet_h tall, n notches on
    one long edge: see the head size and the PETG stringing between them before printing whole panels."""
    length, width = RIVET_STRIP
    body = extrude(rect(0, length, 0, width) - marks(n, 2.0, 0), p.panel_t)
    heads = Sketch() + [Pos(3.0 + k * p.rivet_pitch, y) * Circle(d / 2)
                        for k in range(rivet_count(p)) for y in (width * 0.4, width * 0.75)]
    return Part((body + Pos(0, 0, p.panel_t - 0.01) * extrude(heads, p.printer.layers(p.rivet_h) + 0.01)).solids())


def make(p: Params = P) -> Compound:
    pieces = []
    for i, f in enumerate(GROOVE_FITS):
        pieces.append(Pos(0, 50 * i, 0) * groove_sample(p, f, i + 1))
    pieces.append(Pos(60, 0, 0) * slot_plate(p))
    pieces.append(Pos(60, 25, 0) * tab_strip(p))
    for i, f in enumerate(KEY_FITS):
        pieces.append(Pos(110 + 22 * i, 0, 0) * key_block(p, f, i + 1))
    pieces.append(Pos(110, 35, 0) * key(p))
    pieces.append(Pos(60, 60, 0) * latch_block(p))
    pieces.append(Pos(110, 60, 0) * latch_pier(p))
    for i, f in enumerate(ROD_SEAT_FITS):
        pieces.append(Pos(180 + 25 * i, 0, 0) * rod_seat_sample(p, f, i + 1))
    for i, d in enumerate(RIVET_SIZES):
        pieces.append(Pos(150, 40 + 15 * i, 0) * rivet_strip(p, d, i + 1))
    return Compound(children=pieces)
