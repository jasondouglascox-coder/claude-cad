"""Parts in PRINT orientation: flat on Z = 0, lower color first."""
from build123d import Align, Box, Color, Compound, Cylinder, Part, Pos, Sketch, extrude

from cadkit.shapes import rect
from fitcoupon.params import P, Params

GRAY, ORANGE = Color(0.78, 0.79, 0.80), Color(0.95, 0.55, 0.15)


def hole_x(p: Params, k: int) -> float:
    return p.edge / 2 + p.pitch * (k + 0.5)


def coupon(p: Params = P) -> Compound:
    """Plate with one hole per clearance; variant k gets k+1 raised bars beside its hole, in the second color."""
    plate = Box(p.plate_l, p.plate_w, p.plate_t, align=(Align.MIN, Align.MIN, Align.MIN))
    for k, c in enumerate(p.clearances):
        plate -= Pos(hole_x(p, k), p.plate_w / 2 + 2, 0) * Cylinder((p.peg_d + c) / 2, p.plate_t,
                                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    bars = []
    for k in range(len(p.clearances)):
        x0 = hole_x(p, k) - (k + 1) * (p.mark_w + p.mark_gap) / 2
        for i in range(k + 1):
            x = x0 + i * (p.mark_w + p.mark_gap)
            bars.append(rect(x, x + p.mark_w, p.edge / 2, p.edge / 2 + p.mark_l))
    marks = Pos(0, 0, p.plate_t) * extrude(Sketch() + bars, p.mark_h)
    plate, marks = Part(plate.solids()), Part(marks.solids())
    plate.label, plate.color = "coupon_base", GRAY
    marks.label, marks.color = "coupon_marks", ORANGE
    return Compound(children=[plate, marks], label="coupon")


def peg(p: Params = P) -> Part:
    """The pin, standing on the bed (round in the print plane, so it's truly round)."""
    out = Cylinder(p.peg_d / 2, p.peg_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    out = Pos(p.peg_d / 2, p.peg_d / 2, 0) * out
    out.label = "peg"
    return out
