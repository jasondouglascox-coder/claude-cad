"""Half pier that closes a run: the missing neighbor of the first and last arch halves."""
from build123d import Location, Part, Pos, Rot, Sketch, extrude

from hotrain.joints import rect
from hotrain.params import P, Params


def profile(p: Params) -> Sketch:
    """Same outline as the panels' half pier: plain for arch runs, concrete-look for deck truss runs."""
    s, bw = p.pier_w / 2, (p.bracket_t + p.fit_slide) / 2
    if p.run_style == "deck_truss":
        from hotrain.parts.arch_half import deck_pier
        body = deck_pier(p)
    else:
        body = rect(0, s, -p.pier_depth, 0)
    return body - [
        rect(-1, bw, -p.pier_depth - 1, -p.pier_depth + p.pier_notch),
        rect(-1, bw, -p.latch_top - p.latch_win_h, -p.latch_top),
    ]


def make(p: Params = P) -> Part:
    return Pos(0, p.pier_depth, 0) * extrude(profile(p), p.panel_t)


def place(p: Params, xp: float, y_c: float, run_start: bool) -> Location:
    centre = Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
    if run_start:
        return Pos(xp, y_c, -p.pier_depth) * Rot(0, 0, 180) * centre
    return Pos(xp, y_c, -p.pier_depth) * centre
