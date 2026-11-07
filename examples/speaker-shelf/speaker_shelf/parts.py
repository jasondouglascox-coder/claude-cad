"""Parts in PRINT orientation: flat on Z = 0."""
from build123d import Align, Part, Pos, Sketch, Text, extrude

from cadkit.shapes import rect
from speaker_shelf.params import P, Params


def _engrave(body: Part, labels: list[tuple[float, float, str]], top: float, p: Params) -> Part:
    """Cut each label p.label_depth into the top face, centered on (x, y)."""
    text = Sketch() + [Pos(x, y) * Text(s, p.label_size, align=(Align.CENTER, Align.CENTER)) for x, y, s in labels]
    return Part((body - Pos(0, 0, top - p.label_depth) * extrude(text, p.label_depth)).solids())


def fork_slot_x(p: Params, k: int) -> float:
    """Center of slot k along the fork."""
    return p.fork_tooth * (k + 1) + sum(p.fork_slots[:k]) + p.fork_slots[k] / 2


def rail_fork(p: Params = P) -> Part:
    """A comb: slots open toward +Y, the spine along Y = 0 with each slot's width engraved under it."""
    depth = p.fork_spine + p.fork_depth
    slots = [rect(fork_slot_x(p, k) - w / 2, fork_slot_x(p, k) + w / 2, p.fork_spine, depth + 1)
             for k, w in enumerate(p.fork_slots)]
    body = Part(extrude(Sketch() + rect(0, p.fork_l, 0, depth) - slots, p.fork_h).solids())
    labels = [(fork_slot_x(p, k), p.fork_spine / 2, f"{w:.1f}") for k, w in enumerate(p.fork_slots)]
    out = _engrave(body, labels, p.fork_h, p)
    out.label = "rail_fork"
    return out


def gap_center_x(p: Params) -> float:
    return max(p.gap_steps) / 2


def gap_gauge(p: Params = P) -> Part:
    """A bar centered on X = gap_center_x: step k (from Y = 0, the narrow end going in first) is gap_steps[k] long."""
    cx = gap_center_x(p)
    steps = [rect(cx - L / 2, cx + L / 2, k * p.gap_step_d, (k + 1) * p.gap_step_d + (0.5 if k + 1 < len(p.gap_steps) else 0))
             for k, L in enumerate(p.gap_steps)]
    body = Part(extrude(Sketch() + steps, p.gap_h).solids())
    labels = [(cx, (k + 0.5) * p.gap_step_d, f"{L:g}") for k, L in enumerate(p.gap_steps)]
    out = _engrave(body, labels, p.gap_h, p)
    out.label = "gap_gauge"
    return out
