"""The shelf on its two rails with the speaker in it, for the clash test and the render."""
from build123d import Align, Box, Pos

from speaker_shelf.parts import shelf_body
from speaker_shelf.params import P, Params

RAIL_LEN = 140.0  # shown and tested: enough above and below the shelf
SPEAKER_H = 160.0  # shown only; the real one's height doesn't matter


def rail_boxes(p: Params = P, extra: float = 0.0) -> list[tuple[str, Box]]:
    """Both rails, p.rail square (+ extra), centered on y = 0."""
    s = p.rail + extra
    out = []
    for side, name in ((1, "rail_right"), (-1, "rail_left")):
        x = side * (p.rail_gap / 2 + p.rail / 2)
        out.append((name, Pos(x, 0, -RAIL_LEN / 3) * Box(s, s, RAIL_LEN, align=(Align.CENTER, Align.CENTER, Align.MIN))))
    return out


def speaker_box(p: Params = P) -> Box:
    return Pos(0, -p.speaker_offset, p.floor_t) * Box(p.speaker_w, p.speaker_d, SPEAKER_H,
                                                      align=(Align.CENTER, Align.CENTER, Align.MIN))


def placed_parts(p: Params = P) -> list:
    return [("shelf", shelf_body(p)), ("speaker", speaker_box(p))] + rail_boxes(p)
