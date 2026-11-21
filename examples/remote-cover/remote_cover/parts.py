"""The cover in PRINT orientation: outside face on the bed (Z = 0), inside face up at Z = t, the ear toward +Y, the
tab tips on Y = 0. The plug stands up off the inside face, so nothing but the two little tabs prints over air."""
from build123d import (Align, Axis, Box, BuildSketch, Circle, Cylinder, Kind, Locations, Mode, Part, Pos, Rectangle,
                       Text, chamfer, extrude, fillet, offset)

from remote_cover.params import P, Params


def outline(p: Params = P):
    """The cover's outline at Z = 0: plate plus round-ended ear, corners and shoulders rounded, in by the fit."""
    top = p.y0 + p.h
    ex0, ex1 = p.hole_x - p.ear_w / 2, p.hole_x + p.ear_w / 2
    with BuildSketch() as sk:
        with Locations((0, p.y0)):
            Rectangle(p.w, p.h, align=(Align.MIN, Align.MIN))
        fillet(sk.vertices(), p.corner_r)
        with Locations((ex0, top - 1)):
            Rectangle(p.ear_w, p.hole_y - top + 1, align=(Align.MIN, Align.MIN))
        with Locations((p.hole_x, p.hole_y)):
            Circle(p.ear_w / 2)
        shoulders = [v for v in sk.vertices() if abs(v.Y - top) < 1e-6 and min(abs(v.X - ex0), abs(v.X - ex1)) < 1e-6]
        fillet(shoulders, p.shoulder_r)
        offset(amount=-p.fit, kind=Kind.ARC, mode=Mode.REPLACE)
    return sk.sketch


def cover(p: Params = P, plug_d: float | None = None, mark: bool = True) -> Part:
    """One cover with a plug of plug_d (None: no plug) under the ear, its size engraved on the inside face."""
    body = extrude(outline(p), p.t)
    for x0, x1 in p.tab_xs():  # flush with the inside face, reaching back into the plate to fuse
        body += Pos(x0, 0, p.t - p.tab_t) * Box(x1 - x0, p.y0 + p.fit + 0.5, p.tab_t, align=(Align.MIN,) * 3)
    if plug_d is not None:
        plug = Pos(p.hole_x, p.hole_y, p.t) * Cylinder(plug_d / 2, p.plug_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
        plug = chamfer(plug.edges().sort_by(Axis.Z)[-1], p.plug_chamfer)
        body += plug
        if mark:
            with BuildSketch() as txt:
                Text(f"{plug_d * 10:.0f}", p.mark_size)
            body -= Pos(p.w / 2, p.y0 + p.h / 2, p.t - p.mark_depth) * extrude(txt.sketch, p.mark_depth + 0.1)
    body -= Pos(p.hole_x, p.hole_y, -1) * Cylinder(p.hole_d / 2, p.t + p.plug_h + 2,
                                                  align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = "remote_cover"
    return body
