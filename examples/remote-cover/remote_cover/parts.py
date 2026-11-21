"""The cover in PRINT orientation: outside face on the bed (Z = 0), inside face up at Z = t, the ear toward +Y, in the
pocket's frame (params). The plug stands up off the inside face, so nothing but the two tabs prints over air."""
from build123d import (Align, Axis, Box, BuildSketch, Circle, Cylinder, Kind, Locations, Mode, Part, Pos, Rectangle,
                       Text, chamfer, extrude, fillet, offset)

from remote_cover.params import P, Params


def pocket(p: Params = P):
    """The remote's pocket outline: rounded rectangle plus the round-ended ear recess, shoulders rounded."""
    ex0, ex1 = p.cx - p.ear_w / 2, p.cx + p.ear_w / 2
    with BuildSketch() as sk:
        with Locations((0, p.y0)):
            Rectangle(p.pocket_w, p.pocket_h, align=(Align.MIN, Align.MIN))
        fillet(sk.vertices(), p.pocket_r)
        with Locations((ex0, p.top - 1)):
            Rectangle(p.ear_w, p.ear_tip - p.ear_w / 2 + 1, align=(Align.MIN, Align.MIN))
        with Locations((p.cx, p.top + p.ear_tip - p.ear_w / 2)):
            Circle(p.ear_w / 2)
        shoulders = [v for v in sk.vertices()
                     if abs(v.Y - p.top) < 1e-6 and min(abs(v.X - ex0), abs(v.X - ex1)) < 1e-6]
        fillet(shoulders, p.shoulder_r)
    return sk.sketch


def cover(p: Params = P, mark: bool = True) -> Part:
    """One cover: the pocket less p.clearance on every side, tabs, a plug at the ear's round end, the tongue length
    engraved."""
    clearance = p.clearance
    with BuildSketch() as sk:
        offset(pocket(p), amount=-clearance, kind=Kind.ARC)
    body = extrude(sk.sketch, p.t)
    y_edge = p.y0 + clearance
    for x0, x1 in p.tab_xs():  # flush with the inside face, reaching back into the plate to fuse
        body += Pos(x0, y_edge - p.tab_out, p.t - p.tab_t) * Box(x1 - x0, p.tab_out + 0.5, p.tab_t,
                                                                align=(Align.MIN,) * 3)
    plug = Pos(p.cx, p.hole_y, p.t) * Cylinder(p.plug_d / 2, p.plug_h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    body += chamfer(plug.edges().sort_by(Axis.Z)[-1], p.plug_chamfer)
    if mark:
        with BuildSketch() as txt:
            Text(f"{p.ear_tip * 10:.0f}", p.mark_size)
        body -= Pos(p.cx, p.y0 + p.pocket_h / 2, p.t - p.mark_depth) * extrude(txt.sketch, p.mark_depth + 0.1)
    body -= Pos(p.cx, p.hole_y, -1) * Cylinder(p.hole_d / 2, p.t + p.plug_h + 2,
                                              align=(Align.CENTER, Align.CENTER, Align.MIN))
    body.label = "remote_cover"
    return body
