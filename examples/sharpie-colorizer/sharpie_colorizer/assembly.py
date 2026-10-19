"""Everything in the use frame: X along the bar, the bar's center on Y = Z = 0, +Y toward the outlet side."""
from build123d import Align, Cylinder, Location, Part, Plane, Pos, RectangleRounded, extrude

from sharpie_colorizer.joints import marker_solid
from sharpie_colorizer.layout import base_t, channel_y, top_z
from sharpie_colorizer.params import P, Params
from sharpie_colorizer.parts import block, clip

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def web_top(p: Params = P) -> float:
    """Z of the clip's top web: the block frame's z = 0."""
    return p.bar_h / 2 + p.clip_clear + p.clip_t


def bar(p: Params = P, length: float = 120.0) -> Part:
    return Pos(-length / 2, 0, 0) * extrude(Plane.YZ * RectangleRounded(p.bar_w, p.bar_h, p.bar_r), length)


def _block_frame(p: Params) -> Location:
    return Location((0, 0, web_top(p)))


def marker(p: Params = P, i: int = 0, reading: str = "long", wear: float = 0.0, felt: bool = True) -> Part:
    """Marker i in its socket, felt touching; the gripped section is left out (it's meant to touch)."""
    return _block_frame(p) * block.marker_frame(p, i) * marker_solid(p, reading, wear, felt=felt)


def filament(p: Params = P) -> Part:
    return _block_frame(p) * Pos(0, channel_y(p), 0) * Cylinder(p.filament_d / 2, top_z(p), align=UP)


def tube_paths(p: Params = P) -> list[tuple[str, Part]]:
    """Guide tubes from each socket floor: straight up from the inlet, straight down past the bar from the outlet."""
    x, y = 0, channel_y(p)
    inlet_floor = web_top(p) + top_z(p) - p.tube_depth
    outlet_floor = web_top(p) + p.tube_depth
    bottom = -p.bar_h / 2 - 20
    return [("inlet_tube", Pos(x, y, inlet_floor) * Cylinder(p.tube_od / 2, p.tube_depth + 60, align=UP)),
            ("outlet_tube", Pos(x, y, bottom) * Cylinder(p.tube_od / 2, outlet_floor - bottom, align=UP))]


def lock_pin(p: Params = P) -> Part:
    """A 1.75 mm filament stub down through the block's base into the rail: keeps the block from sliding off."""
    rail_top = web_top(p) + p.rail_h + p.rail_grow
    z0, z1 = rail_top - p.pin_depth + 0.2, web_top(p) + base_t(p) + p.pin_proud
    return Pos(0, 0, z0) * Cylinder(p.filament_d / 2, z1 - z0, align=UP)


def placed_parts(p: Params = P, reading: str = "long", wear: float = 0.0) -> list[tuple[str, Part]]:
    """Bar, clip, block, markers and tubes, for clash checks and renders. Not the filament: felt touches it."""
    out = [("bar", bar(p)), ("clip", clip.place(p) * clip.make(p)), ("block", block.place(p) * block.make(p))]
    out += [(f"marker_{i}", marker(p, i, reading, wear)) for i in range(len(p.azimuths_deg))]
    return out + tube_paths(p) + [("lock_pin", lock_pin(p))]
