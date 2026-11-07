"""Parts in PRINT orientation: flat on Z = 0."""
from build123d import Align, Part, Plane, Pos, Sketch, Text, extrude, mirror

from cadkit.shapes import poly, rect
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


# The shelf, in the rail frame: rails centered on y = 0 at x = ±(rail_gap + rail) / 2, the speaker forward (-y).
# You push it on from the front: each rail slides in from behind, past a hook on a flexing arm, which snaps behind it.


def rail_outer_x(p: Params) -> float:
    return p.rail_gap / 2 + p.rail


def hook_end_y(p: Params) -> float:
    """The back end of each arm: the hook's tip, then a 45-degree lead-in as deep as the hook."""
    return p.rail / 2 + p.hook_tip + p.hook_depth


def _clip_side(p: Params) -> tuple[list, list, list]:
    """The +x clip as (floor, full-height, clip-height) sketches; the -x one is its mirror."""
    r, xo = p.rail / 2, rail_outer_x(p)
    ox = p.speaker_w / 2 + p.speaker_clear + p.wall  # pocket outside
    front = -p.speaker_offset - p.speaker_d / 2 - p.speaker_clear - p.wall
    xa = xo + p.arm_gap  # arm inner face
    y_end = hook_end_y(p)
    root_y = y_end - p.arm_free
    floor = [rect(ox - 1, xa - p.arm_slot, front, -r),  # wing in front of the rail
             rect(ox - 1, xa + p.arm_t, front, root_y)]  # the arm's root
    clip = [rect(ox - 1, xa - p.arm_slot, -r - p.jaw_t, -r),  # front jaw
            rect(xa, xa + p.arm_t, front, y_end),  # arm
            poly((xo - p.hook_depth, r), (xa + p.arm_t, r), (xa + p.arm_t, y_end), (xo, y_end),
                 (xo - p.hook_depth, r + p.hook_tip)),  # hook, lead-in on its back
            rect(xa + p.arm_t - 1, xa + p.arm_t + p.tab, y_end - p.tab_w, y_end)]  # finger tab
    return floor, [], clip


def shelf_body(p: Params = P) -> Part:
    """The shelf in the rail frame, floor on Z = 0."""
    px, py = p.speaker_w / 2 + p.speaker_clear, p.speaker_d / 2 + p.speaker_clear
    cy = -p.speaker_offset
    pocket_out = rect(-px - p.wall, px + p.wall, cy - py - p.wall, cy + py + p.wall)
    floor, _, clip = _clip_side(p)
    floor_sk = Sketch() + [pocket_out] + floor + [mirror(s, Plane.YZ) for s in floor]
    clip_sk = Sketch() + clip + [mirror(s, Plane.YZ) for s in clip]
    walls_sk = Sketch() + [pocket_out] - [rect(-px, px, cy - py, cy + py)]
    out = extrude(floor_sk, p.floor_t) + extrude(walls_sk, p.wall_h) + extrude(clip_sk, p.clip_h)
    out = Part(out.solids()) if len(out.solids()) == 1 else out
    out.label = "speaker_shelf"
    return out


def shelf(p: Params = P) -> Part:
    """Print orientation: as it sits, floor down, moved onto the bed's positive quadrant."""
    body = shelf_body(p)
    bb = body.bounding_box()
    out = Pos(-bb.min.X, -bb.min.Y, 0) * body
    out.label = "speaker_shelf"
    return out
