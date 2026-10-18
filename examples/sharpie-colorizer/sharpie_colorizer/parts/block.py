"""The marker block: a column around the vertical filament channel, a tilted boss per marker, a base with the slot
that slides onto the clip's rail. Prints as it stands (base on the bed); every bore leans at most tilt_deg."""
import math

from build123d import Align, Box, Cone, Cylinder, Location, Part, Plane, Pos, Rectangle, Rot, extrude

from cadkit.shapes import poly

from sharpie_colorizer.joints import marker_cavity, rail_profile, tube_socket
from sharpie_colorizer.layout import base_t, boss_r, channel_y, column_r, mouth_l, tip_point, top_z
from sharpie_colorizer.params import P, Params

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def marker_frame(p: Params = P, i: int = 0) -> Location:
    """Marker i's frame in the block frame: origin at its felt point, +Z along its axis (up and out)."""
    return (Location(tip_point(p, i)) * Location((0, 0, 0), (0, 0, 1), p.azimuths_deg[i]) *
            Location((0, 0, 0), (0, 1, 0), p.tilt_deg))


def body(p: Params = P) -> Part:
    """The block before any cuts (block frame)."""
    y0 = -(p.rail_head / 2 + p.rail_clear + p.wall)
    base = Pos(-p.clip_w / 2, y0, 0) * Box(p.clip_w, channel_y(p) + column_r(p) - y0, base_t(p),
                                          align=(Align.MIN,) * 3)
    column = Pos(0, channel_y(p), 0) * Cylinder(column_r(p), top_z(p), align=UP)
    out = base + column
    for i in range(len(p.azimuths_deg)):
        out += marker_frame(p, i) * Cylinder(boss_r(p), mouth_l(p), align=UP)
    return Part(out.solids())


def make_use(p: Params = P) -> Part:
    """The block in the block frame: z = 0 on the clip's top web, channel at (0, channel_y)."""
    at = Pos(0, channel_y(p), 0)
    out = body(p)
    out -= at * Cylinder(p.channel_d / 2, top_z(p), align=UP)
    out -= at * tube_socket(p)
    out -= at * Cone(p.tube_fit_d / 2 + p.bed_chamfer, p.tube_fit_d / 2, p.bed_chamfer, align=UP)
    out -= Pos(0, channel_y(p), top_z(p)) * Rot(180, 0, 0) * tube_socket(p)
    for i in range(len(p.azimuths_deg)):
        out -= marker_frame(p, i) * marker_cavity(p)
    out -= Pos(-p.clip_w, 0, 0) * extrude(Plane.YZ * _slot(p), 2 * p.clip_w)
    out -= Cylinder(p.pin_hole_d / 2, base_t(p), align=UP)  # lock pin, down into the rail
    return Part(out.solids())


def _slot(p: Params):
    """The rail slot with its peaked roof, chamfered bed_chamfer where it meets the bed (elephant foot)."""
    slot = rail_profile(p, p.rail_clear, peaked=True)
    half0 = (slot & Pos(0, 0.0) * Rectangle(40, 0.001)).bounding_box().size.X / 2
    slope = (p.rail_head - p.rail_neck) / 2 / p.rail_h
    v = p.bed_chamfer + 0.1  # end just inside the slot's flank, so no ledge is left where they meet
    up, w = half0 + slope * v - 0.02, half0 + p.bed_chamfer
    return slot + poly((-w, -1), (w, -1), (w, 0), (up, v), (-up, v), (-w, 0))


def _offset(p: Params) -> tuple[float, float]:
    bb = body(p).bounding_box()
    return -bb.min.X, -bb.min.Y


def make(p: Params = P) -> Part:
    """Print orientation: as it's used, base on the bed, moved into the first quadrant."""
    out = Pos(*_offset(p), 0) * make_use(p)
    out.label = "block"
    return out


def place(p: Params = P) -> Location:
    """Print frame -> use frame: the base sits on the clip's top web."""
    dx, dy = _offset(p)
    return Location((-dx, -dy, p.bar_h / 2 + p.clip_clear + p.clip_t))
