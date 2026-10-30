"""The eyes, drawn: each is a smooth outline (pointed at its inner corner, as in the logo) with a brown rim a line
wide, a brown iris, a white crescent between them, and two white glints. Two colors: the logo's olive iris rim
becomes part of the white crescent."""
from dataclasses import dataclass

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from . import art as A
from . import ears as E
from . import vec as V
from .params import P, Params


@dataclass
class Eye:
    outer: Polygon  # the whole eye
    brown: object  # rim + iris
    white: object  # crescent + glints
    iris: tuple  # (x, y, r)


def shapes(p: Params = P) -> list[Eye]:
    """Each eye in the design frame (moved down with the figure)."""
    dy = E.drop(p, A.load(p))
    out = []
    for pts, corner, (ix, iy, ir), glints in zip(p.eye_shapes, p.eye_corners, p.eye_irises, p.eye_glints):
        loop = [corner, *pts, corner]  # a curve that starts and ends at the corner: smooth all round but there
        outer = Polygon(E.curve([(x, y - dy) for x, y in loop]).coords).buffer(0)
        outer = outer.buffer(-p.eye_tip_r).buffer(p.eye_tip_r, quad_segs=32)  # a needle tip meshes badly
        iris = Point(ix, iy - dy).buffer(ir, quad_segs=64)
        for x, y, r in glints:
            if 2 * r < p.eye_glint_min_d - 1e-9:
                raise ValueError(f"glint at ({x}, {y}) is {2 * r} mm across, under eye_glint_min_d {p.eye_glint_min_d}")
        dots = unary_union([Point(x, y - dy).buffer(r, quad_segs=32) for x, y, r in glints])
        crescent = outer.buffer(-p.line_w).difference(iris)
        white = V.multi(unary_union([crescent, dots]))
        out.append(Eye(outer, V.multi(outer.difference(white)), white, (ix, iy - dy, ir)))
    return out
