"""Every part placed on the wall, plus the environment (wall, hanging screw) for the clash test."""
import math

from build123d import Align, Box, Cylinder, Pos, Rot, Shape

from sunflower import layout
from sunflower.params import Params
from sunflower.parts import center, pin, quarter


def placed_parts(p: Params) -> list[tuple[str, Shape]]:
    out = []
    for layer in ("back", "front"):
        part = quarter.make(p, layer)
        out += [(f"{layer}_{q}", quarter.place(p, layer, q) * part) for q in range(4)]
    for body in center.make(p).children:
        out.append((body.label, center.place(p) * body))
    snap = pin.make(p)
    out += [(f"pin_{k}", pin.place(p, a) * snap) for k, a in enumerate(layout.pin_angles(p))]
    return out


def environment(p: Params) -> list[tuple[str, Shape]]:
    """The wall (touching the flat backs) and the screw hanging quarter 0 at the top of its keyhole."""
    wall = Pos(0, 0, -5) * Box(2 * p.diameter, 2 * p.diameter, 5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    head_d, head_h, shank_d = p.screw
    a = math.radians(layout.back_start(p) + 45)
    r = p.key_r[1]
    at = Pos(r * math.cos(a), r * math.sin(a), 0)
    mn = (Align.CENTER, Align.CENTER, Align.MIN)
    return [("wall", wall),
            ("screw_shank", at * Cylinder(shank_d / 2, p.key_lip, align=mn)),
            ("screw_head", at * Pos(0, 0, p.key_lip) * Cylinder(head_d / 2, head_h, align=mn))]
