"""The spacer in PRINT orientation: lying flat on the bed, the pan's 'up' along +Y, its thickness t in Z."""
from build123d import BuildSketch, Circle, Locations, Mode, Part, Polygon, Pos, extrude, fillet

from loaf_spacer.params import P, Params


def center_x(p: Params = P) -> float:
    """The sheet's widest point starts at X = 0, so it sits in the first quadrant like every other part."""
    return p.top_w / 2 - p.fit


def outline(p: Params = P) -> list[tuple[float, float]]:
    """Half-widths up the pan, less the fit each side, then the tab: one closed outline, centered on X = 0."""
    b, w, tw = p.bottom_w / 2 - p.fit, p.top_w / 2 - p.fit, p.tab_w / 2
    right = [(b, 0), (b, p.wall_h), (w, p.slant_top_h), (w, p.sheet_h), (tw, p.sheet_h), (tw, p.height)]
    return right + [(-x, y) for x, y in reversed(right)]


def spacer(p: Params = P) -> Part:
    """Pan cross-section with a tab and finger hole on top, rounded where a hand or the dough would catch."""
    w, tw = p.top_w / 2 - p.fit, p.tab_w / 2
    with BuildSketch() as sk:
        Polygon(*outline(p), align=None)
        # look the vertices up fresh each time: a fillet replaces the sketch, and old vertices stop matching
        at = lambda pts: [v for v in sk.vertices()
                          if any(abs(v.X - x) < 1e-6 and abs(v.Y - y) < 1e-6 for x, y in pts)]
        fillet(at([(w, p.sheet_h), (-w, p.sheet_h), (tw, p.sheet_h), (-tw, p.sheet_h)]), p.corner_r)
        fillet(at([(tw, p.height), (-tw, p.height)]), p.tab_r)
        with Locations((0, p.hole_center_h)):
            Circle(p.hole_d / 2, mode=Mode.SUBTRACT)
    out = Pos(center_x(p), 0, 0) * Part(extrude(sk.sketch, p.t).solids())
    out.label = "loaf_spacer"
    return out
