"""The clip: snaps over the A1's top frame bar and carries the dovetail rail the block slides onto. It prints lying
on its profile, so the walls that flex while it snaps on bend along the layers."""
from build123d import Circle, Location, Part, Plane, Pos, extrude

from cadkit.shapes import poly

from sharpie_colorizer.joints import clip_profile
from sharpie_colorizer.params import P, Params


def _corner(p: Params) -> tuple[float, float]:
    """Profile origin (the bar's center) in the print frame."""
    return p.bar_w / 2 + p.clip_clear + p.clip_t, p.bar_h / 2 + p.clip_clear + p.clip_t


def make(p: Params = P) -> Part:
    out = Pos(*_corner(p), 0) * Part(extrude(clip_profile(p, p.hook), p.clip_w).solids())
    # lock-pin hole down into the rail's top at mid-width: a teardrop pointing up in print, so it needs no bridge
    r = p.pin_hole_d / 2
    drop = Circle(r) + poly((-r * 0.7071, r * 0.7071), (r * 0.7071, r * 0.7071), (0, r * 1.4142))
    cx, cy = _corner(p)
    rail_top = cy + p.bar_h / 2 + p.clip_clear + p.clip_t + p.rail_h
    out -= Pos(cx, rail_top, p.clip_w / 2) * extrude(Plane.XZ * drop, p.pin_depth)
    out = Part(out.solids())
    out.label = "clip"
    return out


def place(p: Params = P) -> Location:
    """Print frame -> use frame: profile (u, v) -> (Y, Z), thickness -> X, centered on X = 0."""
    cx, cy = _corner(p)
    return Location(Plane(origin=(-p.clip_w / 2, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))) * Location((-cx, -cy, 0))
