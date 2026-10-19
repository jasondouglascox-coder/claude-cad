"""The clip: snaps over the A1's top frame bar and carries the dovetail rail the block slides onto. It prints lying
on its profile, so the walls that flex while it snaps on bend along the layers."""
from build123d import Circle, Location, Part, Plane, Pos, extrude

from cadkit.shapes import poly

from sharpie_colorizer.joints import clip_profile
from sharpie_colorizer.parts.fittest import _with_marks, wall_bars
from sharpie_colorizer.params import P, Params


def _corner(p: Params) -> tuple[float, float]:
    """Profile origin (the bar's center) in the print frame."""
    return p.bar_w / 2 + p.clip_clear_w + p.clip_t, p.bar_h / 2 + p.clip_clear + p.clip_t


def make(p: Params = P, rail_grow: float | None = None) -> Part:
    rail_grow = p.rail_grow if rail_grow is None else rail_grow
    out = Pos(*_corner(p), 0) * Part(extrude(clip_profile(p, p.hook, rail_grow), p.clip_w).solids())
    # lock-pin hole down into the rail's top at mid-width: a teardrop pointing up in print, so it needs no bridge
    r = p.pin_hole_d / 2
    drop = Circle(r) + poly((-r * 0.7071, r * 0.7071), (r * 0.7071, r * 0.7071), (0, r * 1.4142))
    cx, cy = _corner(p)
    rail_top = cy + p.bar_h / 2 + p.clip_clear + p.clip_t + p.rail_h + rail_grow
    out -= Pos(cx, rail_top, p.clip_w / 2) * extrude(Plane.XZ * drop, p.pin_depth)
    out = Part(out.solids())
    out.label = "clip"
    return out


def variants(p: Params = P) -> list[tuple[str, Part]]:
    """The clip reprint plate: one clip per rail_grows size, clip k with k + 1 bars on its top face."""
    out = []
    for k, g in enumerate(p.rail_grows):
        part = _with_marks(make(p, g), wall_bars(p, k + 1), p.clip_w, p.mark_h)
        part.label = f"clip_rail_{k + 1}"
        out.append((part.label, part))
    return out


def place(p: Params = P) -> Location:
    """Print frame -> use frame: profile (u, v) -> (Y, Z), thickness -> X, centered on X = 0."""
    cx, cy = _corner(p)
    return Location(Plane(origin=(-p.clip_w / 2, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))) * Location((-cx, -cy, 0))
