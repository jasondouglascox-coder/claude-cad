"""The adapter in PRINT orientation: base disc on the bed, collar up, candle hole open to the sky."""
from build123d import Align, Axis, Cylinder, Part, Pos, chamfer, fillet

from candle.params import P, Params

UP = (Align.CENTER, Align.CENTER, Align.MIN)


def center(p: Params = P) -> tuple[float, float]:
    """Sitting in the first quadrant, like every other part, so plate packing starts from a clean corner."""
    return p.base_d / 2, p.base_d / 2


def adapter(p: Params = P) -> Part:
    """A Ø base_d disc with a collar holding the candle depth deep; the disc's top is the candle's floor."""
    body = Cylinder(p.base_d / 2, p.base_t, align=UP) + Pos(0, 0, p.base_t) * Cylinder(p.collar_d / 2, p.depth, align=UP)
    root = body.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[1].sort_by(lambda e: e.radius)[0]
    body = fillet(root, p.root_fillet)
    body -= Pos(0, 0, p.base_t) * Cylinder(p.candle_d / 2, p.depth, align=UP)
    mouth = body.edges().filter_by(Axis.Z, reverse=True).group_by(Axis.Z)[-1].sort_by(lambda e: e.radius)[0]
    body = chamfer(mouth, p.mouth_chamfer)
    out = Pos(*center(p), 0) * body
    out.label = "candle_adapter"
    return out
