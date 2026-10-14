import math

import pytest
from build123d import Align, Box, Pos, Rot

from hotrain import assembly
from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain.params import INCH, P
from hotrain.parts import arch_half


@pytest.fixture(scope="module", params=["inside", "bridge"])
def corner(request):
    c = C.inside_corner() if request.param == "inside" else C.bridge_corner()
    return c, A.placed_parts(P, c)


def test_no_clashes_including_cables(corner):
    c, items = corner
    assert assembly.find_clashes(items + A.cables(P, c)) == []


def test_part_counts(corner):
    c, items = corner
    n = c.n_in + P.curve_spans + c.n_out
    names = [n for n, _ in items]
    assert sum(x.startswith("deck") and not x.endswith("_steel") for x in names) == n
    assert sum(x.startswith("frame") for x in names) == 2 * n
    assert sum(x.startswith("floor_beam") for x in names) == n - 1
    assert sum(x.startswith("deep") for x in names) == len(c.deep)


def test_60ft_car_clears_frames(corner):
    """Sweep a 60 ft car body (trucks on the true centerline) around the corner."""
    c, items = corner
    frames = [s for n, s in items if n.startswith("frame")]
    body_l, trucks = 60 * 12 * INCH / 87.1, 42 * 12 * INCH / 87.1
    total = C.path_length(P, c)
    t = 0.0
    while t + trucks <= total:
        a, b = C.track_point(P, c, t), C.track_point(P, c, t + trucks)
        cx, cy = (a.x + b.x) / 2, (a.y + b.y) / 2
        hd = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        car = Pos(cx, cy, P.rail_top + 3) * Rot(0, 0, hd) * Box(body_l, 2 * P.car_half_w, 50,
                                                                    align=(Align.CENTER, Align.CENTER, Align.MIN))
        for f in frames:
            assert (car & f).volume < 1e-6, f"car at t={t:.0f} hits a frame"
        t += 25


def test_viaduct_pier_seats_in_entry_anchor():
    """A viaduct bay ending at the corner's entry anchor drops its pier half into the anchor's slots."""
    items = dict(A.placed_parts(P, C.inside_corner()))
    b = 16 * INCH
    half = arch_half.make(P, b)
    for y in P.rail_ys:
        placed = arch_half.place(P, -b, b, y, end=True) * half
        assert (placed & items["anchor_in"]).volume < 1e-6
        assert placed.distance_to(items["anchor_in"]) < 0.2


def test_layout_sheet_positions():
    rows = C.layout_sheet(P, C.inside_corner())
    by = {r[0]: r for r in rows}
    assert by["anchor (wall A)"][2] == pytest.approx(C.curve_start_x(P, C.inside_corner()) + P.curve_r + P.track_offset)
    assert by["anchor (wall B)"][2] == by["anchor (wall A)"][2]  # symmetric corner


def walls(c):
    """Room walls as solids around a corner (corner frame)."""
    from build123d import Box
    o, big = P.track_offset, 3000
    xb = C.curve_start_x(P, c) + P.curve_r + o
    out = [Pos(-big / 2, -o - 100, -500) * Box(big + 2 * xb, 100, 1000, align=(Align.CENTER, Align.MIN, Align.MIN))]
    if c.wall_b:
        out.append(Pos(xb, -o - 100, -500) * Box(100, big, 1000, align=(Align.MIN, Align.MIN, Align.MIN)))
    else:  # bump-out: beyond the face line, past the bump-out's top face
        out.append(Pos(xb, C.portals(P, c)[-1].y, -500) * Box(big, big, 1000, align=(Align.MIN, Align.MIN, Align.MIN)))
    return out


def test_nothing_inside_the_walls(corner):
    c, items = corner
    for w in walls(c):
        for n, s in items + A.cables(P, c):
            assert (s & w).volume < 1e-6, f"{n} goes into a wall"


@pytest.mark.slow
def test_viaduct_runs_meet_both_ends_cleanly(corner):
    """A viaduct bay ending at the entry anchor and one starting at the exit anchor clash with nothing."""
    from hotrain import layout as L
    c, items = corner
    b = 16 * INCH
    before = [(f"v_in_{n}", Pos(-b, 0, 0) * s) for n, s in assembly.placed_parts(P, [b], (L.FREE, L.CORNER))]
    pn = C.portals(P, c)[-1]
    after = [(f"v_out_{n}", A.wall_b_frame(P, c) * Pos(pn.y, 0, 0) * s)
             for n, s in assembly.placed_parts(P, [b], (L.CORNER, L.FREE))]
    clashes = [x for x in assembly.find_clashes(items + before + after)
               if x[0].startswith("v_") != x[1].startswith("v_")]
    assert clashes == []


def test_lines_run_from_tie_ends_to_ceiling_anchors(corner):
    c, items = corner
    lines = A.cables(P, c)
    anchors = [s for n, s in items if n.startswith("ceiling_anchor")]
    assert len(lines) == len(anchors) == 2 * len(c.ceiling)
    for (n, s), a in zip(lines, anchors):
        bb, ab = s.bounding_box(), a.bounding_box()
        assert bb.min.Z == pytest.approx(P.tie_h, abs=1e-6)  # wrapped around tie ends
        assert bb.max.Z == pytest.approx(ab.min.Z, abs=1e-6)  # meets the anchor's line holes
        assert ab.max.Z == pytest.approx(P.rail_top + P.rail_top_below_ceiling)
        assert ab.min.X < bb.center().X < ab.max.X and ab.min.Y < bb.center().Y < ab.max.Y


def test_lines_wrap_tie_ends_outside_the_trusses(corner):
    """Each line passes through the deck's tie-end zone (outside the edge beam), not a frame."""
    from hotrain.corner_layout import line_u
    assert P.bow_frame_y + P.bow_edge_w / 2 < line_u(P) < P.bow_frame_y + P.bow_edge_w


def test_bus_through_floor_beam_hooks_clears_everything(corner):
    c, items = corner
    clashes = assembly.find_clashes(items + A.bus(P, c))
    # wire segments overlap each other at the hooks by construction; only wire-vs-part counts
    assert [x for x in clashes if x[0].startswith("bus") != x[1].startswith("bus")] == []


def test_rods_run_past_both_anchors(corner):
    c, items = corner
    d = dict(items)
    for side in ("inner", "outer"):
        rod = d[f"rod_{side}"]
        for anchor in ("anchor_in", "anchor_out"):
            assert (rod & d[anchor]).volume < 1e-6
    lens = C.rod_cut_lengths(P, c)
    for side in ("inner", "outer"):
        assert lens[side] == pytest.approx(C.rod_length(P, c, 1 if side == "inner" else -1) + 2 * P.rod_tail, abs=0.01)
        assert lens[side] < 6 * 12 * INCH


def test_bus_stays_out_of_the_walls(corner):
    c, _ = corner
    for w in walls(c):
        for n, s in A.bus(P, c):
            assert (s & w).volume < 1e-6, f"{n} goes into a wall"


def test_decks_are_single_painted_parts(corner):
    """Each deck is one part (one solid) with gray tie plates painted on brown ties."""
    from cadkit import paint
    from hotrain import room
    c, items = corner
    decks = [s for n, s in items if n.startswith("deck")]
    assert len(decks) == c.n_in + P.curve_spans + c.n_out
    assert not any(n.endswith("_steel") for n, _ in items)
    d = decks[0]
    assert len(d.solids()) == 1
    split = paint.display_parts(d)  # a placed copy of a painted prototype: brown ties + gray tie plates
    assert split is not None
    cols = {tuple(round(v, 3) for v in tuple(c)[:3]) for _, c in split}
    assert cols == {tuple(round(v, 3) for v in tuple(room.IRON)[:3]), tuple(round(v, 3) for v in tuple(room.TIE_BROWN)[:3])}
