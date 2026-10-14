"""Room-side handrail piece: posts on the long ties, pegs into the tie sockets. Arch runs get a top and
mid bar at handrail_h; deck truss runs get a short single-bar walkway railing at dt_handrail_h."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain import layout as L
from hotrain.joints import rect
from hotrain.params import Params


def height(p: Params) -> float:
    """Railing top above the rail top."""
    return p.dt_handrail_h if p.run_style == "deck_truss" else p.handrail_h


def make(p: Params, piece: L.HandrailPiece) -> Part:
    """Print orientation: profile flat on the bed, X along the track from piece.x_start, Y = height above tie underside."""
    ln, top, b = piece.x_end - piece.x_start, p.rail_top + height(p), p.handrail_bar
    zm = (p.tie_h + top) / 2
    shapes = [rect(0, ln, top - b, top)]
    if p.run_style != "deck_truss":
        shapes.append(rect(0, ln, zm - b / 2, zm + b / 2))
    for x in (x - piece.x_start for x in piece.posts):
        shapes.append(rect(x - p.handrail_post_w / 2, x + p.handrail_post_w / 2, p.tie_h, top))
        shapes.append(rect(x - p.peg_w / 2, x + p.peg_w / 2, 0, p.tie_h))
    return extrude(Sketch() + shapes, p.handrail_t)


def place(p: Params, piece: L.HandrailPiece) -> Location:
    return Pos(piece.x_start, p.handrail_offset + p.handrail_t / 2, 0) * Rot(90, 0, 0)
