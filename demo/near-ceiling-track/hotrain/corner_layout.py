"""Corner geometry. Corner frame: track enters along +X on y = 0 at portal P0, turns left (toward +Y)
around a curve of radius R, and leaves along +Y. The walls are on the outside (right) of the turn:
wall A at y = -track_offset; for an inside corner wall B is at x = curve end x + track_offset."""
import math
from dataclasses import dataclass

from hotrain.params import P, Params


@dataclass(frozen=True)
class Pose:
    x: float
    y: float
    heading: float  # degrees, 0 = +X


@dataclass(frozen=True)
class Span:
    index: int
    a: Pose
    b: Pose
    curved: bool


@dataclass(frozen=True)
class Corner:
    name: str
    n_in: int
    n_out: int
    wall_b: bool  # True for an inside corner (wall along the exit straights)
    ceiling: tuple  # portal indices hung from the ceiling
    deep: tuple  # (portal index, "A" | "B") deep wall brackets


def inside_corner() -> Corner:
    return Corner("inside", 1, 1, True, (), ((3, "A"), (4, "B")))


def bridge_corner() -> Corner:
    return Corner("bridge", 1, 3, False, (6,), ((3, "A"),))


def step_deg(p: Params) -> float:
    return 90 / p.curve_spans


def curve_start_x(p: Params, c: Corner) -> float:
    return c.n_in * p.bow_span


def portals(p: Params, c: Corner) -> list[Pose]:
    r, s, x1 = p.curve_r, p.bow_span, curve_start_x(p, c)
    out = [Pose(i * s, 0.0, 0.0) for i in range(c.n_in + 1)]
    for k in range(1, p.curve_spans + 1):
        a = math.radians(k * step_deg(p))
        out.append(Pose(x1 + r * math.sin(a), r - r * math.cos(a), k * step_deg(p)))
    xe, ye = x1 + r, r
    out += [Pose(xe, ye + j * s, 90.0) for j in range(1, c.n_out + 1)]
    return out


def spans(p: Params, c: Corner) -> list[Span]:
    ps = portals(p, c)
    return [Span(i, ps[i], ps[i + 1], c.n_in <= i < c.n_in + p.curve_spans) for i in range(len(ps) - 1)]


def track_point(p: Params, c: Corner, t: float) -> Pose:
    """Pose on the true track centerline at arc length t from P0."""
    r, x1 = p.curve_r, curve_start_x(p, c)
    if t <= x1:
        return Pose(t, 0.0, 0.0)
    arc = r * math.pi / 2
    if t <= x1 + arc:
        a = (t - x1) / r
        return Pose(x1 + r * math.sin(a), r - r * math.cos(a), math.degrees(a))
    return Pose(x1 + r, r + (t - x1 - arc), 90.0)


def path_length(p: Params, c: Corner) -> float:
    return curve_start_x(p, c) + p.curve_r * math.pi / 2 + c.n_out * p.bow_span


def chord_sagitta(p: Params) -> float:
    return p.bow_span ** 2 / (8 * p.curve_r)


def wall_offset(p: Params, c: Corner, pose: Pose) -> float:
    """Distance from the nearest real wall to a point on the track."""
    d = pose.y + p.track_offset
    if c.wall_b:
        d = min(d, curve_start_x(p, c) + p.curve_r + p.track_offset - pose.x)
    return d


def rod_length(p: Params, c: Corner, side: int) -> float:
    """Rod length between the end anchors (side +1 = inner rod, toward the curve center)."""
    straight = (c.n_in + c.n_out) * p.bow_span
    return straight + (p.curve_r - side * p.rod_y) * math.pi / 2


def rod_cut_lengths(p: Params, c: Corner) -> dict:
    """Cut length of each rod: anchor to anchor plus rod_tail past each anchor."""
    return {"inner": rod_length(p, c, 1) + 2 * p.rod_tail, "outer": rod_length(p, c, -1) + 2 * p.rod_tail}


def line_u(p: Params) -> float:
    """Hanging line, measured from the track: around the tie ends just outside a truss's edge beam."""
    return p.bow_frame_y + p.bow_edge_w / 2 + 1.5


def line_point(p: Params, pt, s: int) -> tuple[float, float]:
    """Plan position of the hanging line on side s (+1 toward the curve center) for ceiling portal pt:
    line_inset into the next span, so it wraps ties rather than the floor beam."""
    a = math.radians(pt.heading)
    u = line_u(p)
    x = pt.x + p.line_inset * math.cos(a) - s * u * math.sin(a)
    y = pt.y + p.line_inset * math.sin(a) + s * u * math.cos(a)
    return x, y


def layout_sheet(p: Params, c: Corner) -> list[tuple[str, str, float]]:
    """(item, how to measure, mm) for marking supports on the walls and ceiling.
    Inside corner: distances from the corner where the walls meet. Bridge corner: along the top wall
    from the bump-out face line; the ceiling drop also gives its distance out from the top wall."""
    ps = portals(p, c)
    xb = curve_start_x(p, c) + p.curve_r + p.track_offset
    a_ref = "from the corner along wall A" if c.wall_b else "along the top wall from the bump-out face line"
    rows = [("anchor (wall A)", a_ref, xb - ps[0].x)]
    if c.wall_b:
        rows.append(("anchor (wall B)", "from the corner along wall B", ps[-1].y + p.track_offset))
    else:
        rows.append(("anchor (bump-out)", "down the bump-out face from its corner (rods slide in it ±9.5 mm)",
                     ps[-1].y + p.track_offset - p.alcove_w))
    for i, wall in c.deep:
        pt = ps[i]
        if wall == "A":
            rows.append((f"6in bracket P{i} (wall A)", a_ref, xb - pt.x))
        else:
            rows.append((f"6in bracket P{i} (wall B)", "from the corner along wall B", pt.y + p.track_offset))
    for i in c.ceiling:
        for s, side in ((1, "inner"), (-1, "outer")):
            x, y = line_point(p, ps[i], s)
            rows.append((f"ceiling anchor P{i} {side}: along", a_ref + " (negative = over the alcove)", xb - x))
            rows.append((f"ceiling anchor P{i} {side}: out", "from the top wall", y + p.track_offset))
    for side, mm in rod_cut_lengths(p, c).items():
        rows.append((f"rod cut length ({side})", "1/4 in aluminum, before bending", mm))
    return rows
