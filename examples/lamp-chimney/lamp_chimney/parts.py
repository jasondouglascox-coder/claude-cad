"""The chimney in PRINT orientation: foot on the bed, neck up, open at both ends."""
from build123d import Align, Axis, Part, Plane, Polygon, Pos, Rectangle, fillet, offset, revolve

from lamp_chimney.params import P, Params


def center(p: Params = P) -> tuple[float, float]:
    """Sitting in the first quadrant, so plate packing starts from a clean corner."""
    return p.foot_d / 2, p.foot_d / 2


def profile(p: Params = P):
    """Half section (x = radius, y = height): the outside line with both shoulder bends rounded, offset in by the
    wall, plus the thick foot ring with a 45-degree chamfer up into the wall."""
    r, rn, h = p.foot_d / 2, p.neck_d / 2, p.height
    outside = Polygon((-1, -1), (r, -1), (r, p.shoulder_z), (rn, p.shoulder_top), (rn, h + 1), (-1, h + 1), align=None)
    outside = fillet(outside.vertices().filter_by(lambda v: 0 < v.Y < h and v.X > 0), p.bend_r)
    band = (outside - offset(outside, -p.wall)) & Rectangle(r + 1, h, align=Align.MIN)
    step = p.foot_t - p.wall
    foot = Polygon((r - p.foot_t, 0), (r, 0), (r, p.foot_h + step), (r - p.wall, p.foot_h + step),
                   (r - p.foot_t, p.foot_h), align=None)
    return band + foot


def chimney(p: Params = P) -> Part:
    body = revolve(Plane.XZ * profile(p), Axis.Z)
    out = Pos(*center(p), 0) * Part(body.solids())
    out.label = "lamp_chimney"
    return out


def on_bed(p: Params = P) -> Part:
    """In the middle of the bed: a corner would clip the outer brim (the slicer stops it at the bed's edge)."""
    out = Pos((p.printer.bed - p.foot_d) / 2, ((p.printer.bed_y or p.printer.bed) - p.foot_d) / 2, 0) * chimney(p)
    out.label = "lamp_chimney"
    return out
