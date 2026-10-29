"""The jig, flat as it prints and as it's used: pivot screw at the origin, the long bar along +X.

A pinwheel: the bar and three short arms, each a strip lying on one side of a line through the pivot, so every arm
has one straight edge exactly on a radius. Draw along the bar for a radius; turn the jig a quarter until a short
arm's edge lies on that line and the bar is on the next quarter."""
import math

from build123d import (Align, Box, Cone, Cylinder, Part, Plane, Polygon, Pos, Rot, Sketch, Text, extrude)

from cadkit.shapes import rect
from circle_jig.params import P, Params


def outline(p: Params = P) -> Sketch:
    """Bar along +X above the X axis, then the short arms a quarter turn apart, each on the same side of its line."""
    w, a = p.w, p.arm
    return Sketch() + [rect(0, p.bar_len, 0, w), rect(-w, 0, 0, a), rect(-a, 0, -w, 0), rect(0, w, -a, 0)]


def bevel(p: Params, length: float) -> Part:
    """Wedge to take off the top of an edge lying along +X at y = 0 (part on +y), from x = 0 to length."""
    tri = Polygon((0, p.t - p.bevel), (0, p.t + 1), (p.bevel + 1, p.t + 1), align=None)
    return extrude(Plane.YZ * tri, length, dir=(1, 0, 0))


def pencil_hole(p: Params) -> Part:
    """Throat at the bottom for the point, a cone above it guiding the pencil down to it."""
    throat = Cylinder(p.throat_d / 2, p.throat_h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cone = Pos(0, 0, p.throat_h) * Cone(p.throat_d / 2, p.sink_r + 0.01 * math.tan(math.radians(p.sink_deg)),
                                        p.t - p.throat_h + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Pos(0, 0, -0.005) * (throat + cone)


def jig(p: Params = P) -> Part:
    body = extrude(outline(p), p.t)
    reach = [p.bar_len, p.arm, p.arm, p.arm]
    for k in range(4):  # each straight edge, from the hub out to its tip
        body -= Rot(0, 0, 90 * k) * Pos(p.w, 0, 0) * bevel(p, reach[k] - p.w)
    body -= Cylinder(p.pivot_d / 2, 3 * p.t)
    labels = []
    for d, r in zip(p.diameters_in, p.radii):
        x = p.hole_x(r)
        body -= Pos(x, p.hole_off, 0) * pencil_hole(p)
        label_y = (p.hole_off + p.sink_r + p.w) / 2
        labels.append(Pos(x, label_y) * Text(str(d), p.label_size, align=(Align.CENTER, Align.CENTER)))
    body += Pos(0, 0, p.t) * extrude(Sketch() + labels, p.label_h)
    out = Part(body.solids())
    out.label = "circle_jig"
    return out


def on_bed(p: Params = P) -> Part:
    """Across the bed's diagonal: the bar is longer than the bed is wide."""
    turned = Rot(0, 0, 45) * jig(p)
    bb = turned.bounding_box()
    usable_x, usable_y = p.printer.usable_x, p.printer.usable_y
    out = Pos((usable_x - bb.max.X - bb.min.X) / 2, (usable_y - bb.max.Y - bb.min.Y) / 2, 0) * turned
    out.label = "circle_jig"
    return out
