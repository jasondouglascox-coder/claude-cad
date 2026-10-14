"""Printability checks shared by tests and the build command."""
from build123d import Shape

from hotrain.params import P, Params


def printable_problems(part: Shape, p: Params = P) -> list[str]:
    """Why this part can't go straight to the A1 as exported. Empty list = fine."""
    probs = []
    if not part.is_valid:
        probs.append("invalid solid")
    if len(part.solids()) != 1:
        probs.append(f"{len(part.solids())} separate solids (expected 1)")
    bb = part.bounding_box()
    if abs(bb.min.Z) > 1e-6:
        probs.append(f"not on the bed: min Z = {bb.min.Z:.3f}")
    if bb.min.X < -1e-6 or bb.min.Y < -1e-6:
        probs.append("extends into negative X/Y")
    if bb.max.X > p.bed_usable or bb.max.Y > p.bed_usable:
        probs.append(f"footprint {bb.max.X:.1f} x {bb.max.Y:.1f} mm exceeds {p.bed_usable:.0f} mm")
    return probs


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
