"""The fit-test plate, printed first: the marker sockets at the block's tilt, the tube sockets, and slices of the
clip with each hook. Each variant k carries k + 1 raised bars; the snug ones go into params.py."""
import math

from build123d import Align, Box, Cone, Cylinder, Location, Part, Pos, Sketch, extrude

from cadkit.shapes import rect
from sharpie_colorizer.joints import clip_profile
from sharpie_colorizer.params import P, Params

MIN = (Align.MIN, Align.MIN, Align.MIN)
UP = (Align.CENTER, Align.CENTER, Align.MIN)


def _bars(p: Params, n: int, x: float, y: float, along_x: bool) -> list[Sketch]:
    """n bars centered on (x, y), each mark_l long along X (or Y), side by side."""
    pitch = p.mark_w + p.mark_gap
    out = []
    for i in range(n):
        o = (i - (n - 1) / 2) * pitch
        if along_x:
            out.append(rect(x - p.mark_l / 2, x + p.mark_l / 2, y + o - p.mark_w / 2, y + o + p.mark_w / 2))
        else:
            out.append(rect(x + o - p.mark_w / 2, x + o + p.mark_w / 2, y - p.mark_l / 2, y + p.mark_l / 2))
    return out


def _with_marks(part: Part, bars: list[Sketch], z: float, mark_h: float) -> Part:
    marks = Pos(0, 0, z - 0.01) * extrude(Sketch() + bars, 0.01 + mark_h)
    return Part((part + marks).solids())


def _strip_dims(p: Params):
    t = math.radians(p.tilt_deg)
    r = max(p.marker_fits) / 2
    x0 = r / math.cos(t) + p.fit_wall  # bore axis at the bed
    lx = x0 + p.fit_h * math.tan(t) + r / math.cos(t) + p.fit_wall
    pitch = 2 * r + p.fit_wall
    return t, x0, lx, pitch


def bore_axis(p: Params = P, k: int = 0) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Bore k of the marker strip: its axis at the bed and its direction (tilted along +X)."""
    t, x0, _, pitch = _strip_dims(p)
    return (x0, p.fit_wall + max(p.marker_fits) / 2 + k * pitch, 0.0), (math.sin(t), 0.0, math.cos(t))


def marker_strip(p: Params = P) -> Part:
    """One tilted bore per marker_fits size, opening on the top and running out through the bed face."""
    t, x0, lx, pitch = _strip_dims(p)
    n = len(p.marker_fits)
    ly = 2 * p.fit_wall + max(p.marker_fits) + (n - 1) * pitch
    strip = Box(lx, ly, p.fit_h, align=MIN)
    bars = []
    for k, d in enumerate(p.marker_fits):
        (ox, oy, _), _ = bore_axis(p, k)
        long = 4 * p.fit_h / math.cos(t)  # ends well outside the block, so no tilted end cap is left inside
        rod = Pos(0, 0, -long / 2) * Cylinder(d / 2, long, align=UP)
        strip -= Location((ox, oy, 0), (0, 1, 0), p.tilt_deg) * rod
        bars += _bars(p, k + 1, p.fit_wall + p.mark_l / 2, oy, along_x=True)
    return _with_marks(Part(strip.solids()), bars, p.fit_h, p.mark_h)


def tube_hole(p: Params = P, k: int = 0) -> tuple[float, float]:
    pitch = max(p.tube_fits) + 2 * p.mark_l
    return p.fit_wall + max(p.tube_fits) / 2 + p.mark_l + k * pitch, p.fit_wall + max(p.tube_fits) / 2


def tube_strip(p: Params = P) -> Part:
    """A through-hole per tube_fits size: the top mouth is the inlet's, the chamfered bed mouth the outlet's."""
    n = len(p.tube_fits)
    x_last, y = tube_hole(p, n - 1)
    lx = x_last + max(p.tube_fits) / 2 + p.mark_l + p.fit_wall
    ly = y + max(p.tube_fits) / 2 + p.mark_l + 2 * p.fit_wall
    strip = Box(lx, ly, p.tube_depth, align=MIN)
    bars = []
    for k, d in enumerate(p.tube_fits):
        x, y = tube_hole(p, k)
        strip -= Pos(x, y, 0) * Cylinder(d / 2, p.tube_depth, align=UP)
        strip -= Pos(x, y, 0) * Cone(d / 2 + p.bed_chamfer, d / 2, p.bed_chamfer, align=UP)
        bars += _bars(p, k + 1, x, ly - p.fit_wall - p.mark_l / 2, along_x=False)
    return _with_marks(Part(strip.solids()), bars, p.tube_depth, p.mark_h)


def bar_center(p: Params = P) -> tuple[float, float]:
    """Where the bar's center sits in a clip slice (print frame)."""
    return p.bar_w / 2 + p.clip_clear_w + p.clip_t, p.bar_h / 2 + p.clip_clear + p.clip_t


def clip_slice(p: Params = P, k: int = 0) -> Part:
    """A slice_w-thick slice of the clip with hooks[k], lying on its profile, with k + 1 bars on a side wall."""
    cx, cy = bar_center(p)
    s = Pos(cx, cy, 0) * extrude(clip_profile(p, p.hooks[k]), p.slice_w)
    return _with_marks(Part(s.solids()), wall_bars(p, k + 1), p.slice_w, p.mark_h)


def wall_bars(p: Params, n: int) -> list[Sketch]:
    """n bars along a clip's side wall, for the top face of anything printed on the clip's profile."""
    cx, cy = bar_center(p)
    wall_x = cx + p.bar_w / 2 + p.clip_clear_w + p.clip_t / 2
    pitch = p.mark_l + p.mark_w + p.mark_gap
    return [rect(wall_x - p.mark_w / 2, wall_x + p.mark_w / 2, cy - p.bar_h / 2 + i * pitch,
                 cy - p.bar_h / 2 + i * pitch + p.mark_l) for i in range(n)]


def fit_items(p: Params = P) -> list[tuple[str, Part]]:
    items = [("marker_strip", marker_strip(p)), ("tube_strip", tube_strip(p))]
    items += [(f"clip_slice_{k + 1}", clip_slice(p, k)) for k in range(len(p.hooks))]
    for name, part in items:
        part.label = name
    return items
