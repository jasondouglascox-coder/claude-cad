"""The ceiling gauge (the user, 2026-10-28): a thin T held against the ceiling with two pencil holes, so every
bracket's (and rod anchor's) screws are marked at the same height round the room. The top screw is 10" below the
ceiling, "makes easy math", and the screws sit at the top of their slots so a bracket can still go up. The arm is
longer than the bed, so the T and the arm print apart and join with a glued dovetail."""
import pytest
from build123d import Box, Pos

from cadkit.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import ceiling_gauge as G


def test_rail_height_follows_the_screws():
    """Screw at the top of its slot: the bracket top is (slot center - travel) above the screw line."""
    assert P.screw_below_ceiling == pytest.approx(10 * INCH)
    tie_underside = P.screw_below_ceiling - (P.screw_zs[0] - P.screw_travel)
    assert P.rail_top_below_ceiling == pytest.approx(tie_underside - P.rail_top)


def test_holes_mark_both_screws_from_the_ceiling_edge():
    g = G.assembled(P)  # gauge frame: x down from the ceiling (the T's top edge at x = 0), y across
    bb = g.bounding_box()
    assert bb.min.X == pytest.approx(0, abs=1e-6)
    assert bb.size.Y == pytest.approx(P.gauge_bar_l, abs=1e-6)  # the T: 4" along the ceiling
    assert bb.size.Z == pytest.approx(P.gauge_t, abs=1e-6)  # thin

    def solid(x, y):
        return (g & (Pos(x, y, P.gauge_t / 2) * Box(0.2, 0.2, 0.2))).volume > 1e-6

    for x in G.hole_xs(P):
        assert not solid(x, 0)  # the pencil hole
        assert solid(x + P.gauge_hole_d / 2 + 0.6, 0) and solid(x - P.gauge_hole_d / 2 - 0.6, 0)
    assert G.hole_xs(P) == pytest.approx([P.screw_below_ceiling, P.screw_below_ceiling + P.screw_zs[1] - P.screw_zs[0]])
    assert bb.max.X > G.hole_xs(P)[-1] + P.gauge_hole_d


def test_braces_square_the_t():
    """Two 45-degree braces from the bar's ends to the arm: material on the line halfway down each."""
    g = G.assembled(P)
    h = P.gauge_bar_l / 2
    for s in (1, -1):
        x, y = P.gauge_bar_w + (h - P.gauge_arm_w / 2) / 2, s * (h + P.gauge_arm_w / 2) / 2
        assert (g & (Pos(x, y, P.gauge_t / 2) * Box(0.5, 0.5, 0.5))).volume > 0


def test_two_pieces_print_flat_and_join():
    t, arm = G.t_piece(P), G.arm_piece(P)
    for part in (t, arm):
        assert len(part.solids()) == 1
        assert printable_problems(part, P.printer) == []
        bb = part.bounding_box()
        assert max(bb.size.X, bb.size.Y) <= P.bed_usable
    assert (G.t_in_gauge(P) & G.arm_in_gauge(P)).volume < 1e-6  # the tab sits in its socket, no clash
    # a probe across the tab's head runs into the socket's walls on both sides
    probe = Pos(P.gauge_split + 0.75 * P.gauge_jig_len, 0, P.gauge_t / 2) * Box(0.3, P.gauge_arm_w - 1.0, 0.5)
    assert (probe & G.arm_in_gauge(P)).volume > 0 and (probe & G.t_in_gauge(P)).volume > 0


def test_build_writes_the_gauge(tmp_path):
    from cadkit import slicers
    from hotrain import build
    assert build.main(["ceiling-gauge", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "ceiling_gauge" / f"ceiling_gauge{slicers.active().project_suffix}").exists()
