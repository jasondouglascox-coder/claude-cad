"""The jig as it's used: pivot screw at the origin, the long bar along +X, flat on Z = 0.

A pinwheel: the bar and three short arms, each a strip lying on one side of a line through the pivot, so every arm
has one straight edge exactly on a radius. Draw along the bar for a radius; turn the jig a quarter until a short
arm's edge lies on that line and the bar is on the next quarter.

The bar is longer than the bed, so it prints as a hub piece (the arms and the bar out past split_after) and a
straight extension, butted at split_x and locked by a bow-tie key dropped in flush across the seam."""
import math

from build123d import Align, Box, Cone, Cylinder, Part, Plane, Polygon, Pos, Rot, Sketch, Text, extrude

from cadkit.plates import Plate
from cadkit.shapes import bowtie, rect

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
    for n, r in zip(p.radii_in, p.radii):
        x = p.hole_x(r)
        body -= Pos(x, p.hole_off, 0) * pencil_hole(p)
        label_y = (p.hole_off + p.sink_r + p.w) / 2
        labels.append(Pos(x, label_y) * Text(str(n), p.label_size, align=(Align.CENTER, Align.CENTER)))
    body += Pos(0, 0, p.t) * extrude(Sketch() + labels, p.label_h)
    out = Part(body.solids())
    out.label = "circle_jig"
    return out


def _piece(p: Params, x0: float, x1: float, label: str) -> Part:
    """The jig between x0 and x1, less the key's socket."""
    big = 2 * p.bar_len
    keep = Pos(x0, -big / 2, -1) * Box(x1 - x0, big, p.t + 2, align=(Align.MIN,) * 3)
    socket = Pos(p.split_x, p.w / 2, -1) * extrude(bowtie(p.key_len, p.key_head, p.key_waist, p.fit_key), p.t + 2)
    out = Part(((jig(p) & keep) - socket).solids())
    out.label = label
    return out


def hub(p: Params = P) -> Part:
    """The arms and the bar out to the seam: on its own it draws up to split_after inches."""
    return _piece(p, -2 * p.arm, p.split_x, "circle_jig_hub")


def extension(p: Params = P) -> Part:
    return _piece(p, p.split_x, p.bar_len + 1, "circle_jig_extension")


def key(p: Params = P) -> Part:
    """The bow-tie key in print orientation: flat, in the first quadrant."""
    out = Pos(p.key_len / 2, p.key_head / 2, 0) * extrude(bowtie(p.key_len, p.key_head, p.key_waist), p.t)
    out = Part(out.solids())
    out.label = "circle_jig_key"
    return out


def key_in_place(p: Params = P) -> Part:
    out = Pos(p.split_x - p.key_len / 2, p.w / 2 - p.key_head / 2, 0) * key(p)
    out.label = "circle_jig_key"
    return out


def bed_angle(p: Params = P) -> float:
    """Turn (degrees) that fits the hub piece on the bed with the most room: near the diagonal, nudged so both spans
    match."""
    w, a, L = p.w, p.arm, p.split_x
    corners = [(L, 0), (L, w), (-w, a), (0, a), (-a, 0), (-a, -w), (w, -a), (0, -a)]

    def span(deg):
        c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        xs, ys = [x * c - y * s for x, y in corners], [x * s + y * c for x, y in corners]
        return max(max(xs) - min(xs), max(ys) - min(ys))

    return min((d / 10 for d in range(300, 601)), key=span)


def _centred(p: Params, part: Part, dy: float = 0.0) -> Part:
    bb = part.bounding_box()
    bed_x, bed_y = p.printer.bed, p.printer.bed_y or p.printer.bed
    out = Pos((bed_x - bb.max.X - bb.min.X) / 2, (bed_y - bb.max.Y - bb.min.Y) / 2 + dy, 0) * part
    out.label = part.label
    return out


def plates(p: Params = P) -> list[Plate]:
    """Hub across the bed's diagonal (with the arms it's longer than the bed is wide); the extension along X with the
    key, and a spare, beside it."""
    turned = Rot(0, 0, bed_angle(p)) * hub(p)
    turned.label = "circle_jig_hub"
    ext = _centred(p, Pos(-p.split_x, 0, 0) * extension(p))
    ext.label = "circle_jig_extension"
    gap = 10.0
    keys = []
    for i, label in enumerate(("circle_jig_key", "circle_jig_key_spare")):
        k = Pos(ext.bounding_box().min.X + i * (p.key_len + gap), ext.bounding_box().max.Y + gap, 0) * key(p)
        k.label = label
        keys.append(k)
    return [Plate("circle_jig_hub", 1, [("circle_jig_hub", _centred(p, turned))]),
            Plate("circle_jig_extension", 1, [("circle_jig_extension", ext)] + [(k.label, k) for k in keys])]
