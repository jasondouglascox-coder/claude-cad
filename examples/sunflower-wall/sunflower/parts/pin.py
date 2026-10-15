"""Snap pin, printed flat (the arms flex along the layers). Profile in XY with its length along +Y: head at y = 0
(against the wall), shank through both hubs, split arrow tip whose barbs snap over the seed head's throat."""
from build123d import Circle, Location, Part, Pos, Rot, extrude

from cadkit.shapes import poly, rect
from sunflower import layout
from sunflower.params import Params

TIP_NARROW = 0.3  # tip half width below the shank's, so it finds the slot


def make(p: Params) -> Part:
    y = layout.pin_y(p)
    w, hl = p.pin_w / 2, p.pin_w / 2 + p.pin_lip
    right = [(hl, 0), (hl, y["head"]), (w, y["head"]), (w, y["barb"]), (w + p.pin_barb, y["barb"]),
             (w - TIP_NARROW, y["tip"])]
    prof = poly(*(right + [(-x, yy) for x, yy in reversed(right)]))
    y0 = y["tip"] - p.pin_slot_len + p.pin_slot_w / 2  # split ends in a half-round: no corner to crack from
    prof = prof - rect(-p.pin_slot_w / 2, p.pin_slot_w / 2, y0, y["tip"] + 1) - Pos(0, y0) * Circle(p.pin_slot_w / 2)
    part = Part((Pos(hl, 0, 0) * extrude(prof, p.pin_t)).solids())
    part.label = "pin"
    return part


def place(p: Params, angle: float) -> Location:
    """Print frame -> standing in its slot at `angle`, head on the wall (z = 0), width radial."""
    hl = p.pin_w / 2 + p.pin_lip
    return Rot(0, 0, angle) * Pos(p.pin_r, 0, 0) * Rot(90, 0, 0) * Pos(-hl, 0, -p.pin_t / 2)
