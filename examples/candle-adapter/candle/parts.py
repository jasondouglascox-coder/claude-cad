"""The adapter in PRINT orientation: flared foot on the bed, collar up, candle hole open to the sky."""
from build123d import (Align, Axis, BuildLine, BuildSketch, Cylinder, Part, Plane, Polyline, Pos, Spline, chamfer,
                       make_face, revolve)

from candle.params import P, Params

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def center(p: Params = P) -> tuple[float, float]:
    """Sitting in the first quadrant, like every other part, so plate packing starts from a clean corner."""
    return p.base_d / 2, p.base_d / 2


def adapter(p: Params = P) -> Part:
    """Revolved profile: a thin edge at Ø base_d that flares up into the collar, which holds the candle depth deep.
    The radius only shrinks going up, so nothing overhangs."""
    r_base, r_collar = p.base_d / 2, p.collar_d / 2
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline((0, p.height), (0, 0), (r_base, 0), (r_base, p.edge_t))
            Spline((r_base, p.edge_t), (r_collar, p.flare_h), tangents=[(-1, p.flare_rise), (0, 1)])
            Polyline((r_collar, p.flare_h), (r_collar, p.height), (0, p.height))
        make_face()
    body = revolve(profile.sketch, Axis.Z)
    body -= Pos(0, 0, p.floor_t) * Cylinder(p.candle_d / 2, p.depth, align=UP)
    mouth = body.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[-1].sort_by(lambda e: e.radius)[0]
    body = chamfer(mouth, p.mouth_chamfer)
    out = Pos(*center(p), 0) * Part(body.solids())
    out.label = "candle_adapter"
    return out
