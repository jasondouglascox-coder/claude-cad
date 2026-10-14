"""Printability checks: cadkit's, on this project's printer, plus the derail-catch check."""
from build123d import Shape

from cadkit import checks
from hotrain.params import P, Params


def printable_problems(part: Shape, p: Params = P) -> list[str]:
    """Why this part can't go straight to the printer as exported. Empty list = fine."""
    return checks.printable_problems(part, p.printer)


def tip_catch_angle(p, rails: list, bay_len: float, max_deg: float = 45.0, step: float = 0.5):
    """Lean (degrees) at which a car body tipping toward the room about the room-side rail head first
    touches a railing part, or None if it would go over within max_deg. The body is a 60 ft car box
    centered mid-bay, from car_sill_h to car_sill_h + car_body_h above the rail top."""
    from build123d import Align, Box, Pos, Rot

    py, pz = p.rail_ctc / 2 + p.rail_head_w / 2, p.rail_top
    body_l = 60 * 12 * 25.4 / 87.1
    car = Pos(bay_len / 2 - body_l / 2, -p.car_half_w, p.rail_top + p.car_sill_h) * Box(
        body_l, 2 * p.car_half_w, p.car_body_h, align=(Align.MIN, Align.MIN, Align.MIN))
    a = 0.0
    while a <= max_deg + 1e-9:
        tipped = Pos(0, py, pz) * Rot(-a, 0, 0) * Pos(0, -py, -pz) * car
        tb = tipped.bounding_box()
        for r in rails:
            rb = r.bounding_box()
            if rb.min.X > tb.max.X or rb.max.X < tb.min.X or rb.min.Y > tb.max.Y or rb.max.Y < tb.min.Y \
                    or rb.min.Z > tb.max.Z or rb.max.Z < tb.min.Z:
                continue
            if (tipped & r).volume > 1e-6:
                return a
        a += step
    return None
