"""The leg clip: under each bracket between two bays, a U slid up over the wall-side truss's two pier legs, its end
walls hooking their outer ends and its middle under the bracket, so the legs' bottoms can't spread (2026-11-06)."""
from dataclasses import replace

import pytest
from build123d import Pos

from cadkit.checks import off_layer_z, open_edges
from hotrain import assembly
from hotrain import layout as L
from hotrain.checks import printable_problems
from hotrain.params import INCH, P
from hotrain.parts import leg_clip

DT = replace(P, run_style="deck_truss")
BAYS = [16 * INCH, 16 * INCH]


@pytest.fixture(scope="module")
def joint():
    """The middle bracket's neighbours in a two-bay deck-truss run, and the clip placed under it."""
    parts = dict(assembly.placed_parts(DT, BAYS, (L.FREE, L.FREE)))
    x = L.pier_xs(BAYS)[1]
    near = {n: s for n, s in parts.items() if s.bounding_box().min.X < x + 60 and s.bounding_box().max.X > x - 60}
    return near, parts["leg_clip1"]


def test_clip_prints_flat_in_one_piece():
    clip = leg_clip.make(DT)
    assert printable_problems(clip, DT) == []
    assert len(clip.solids()) == 1
    assert open_edges(clip) == 0
    assert off_layer_z(clip, DT.printer) == []


def test_clip_sits_under_the_middle_bracket_touching_nothing(joint):
    near, clip = joint
    for name, shape in near.items():
        if name != "leg_clip1":
            assert (shape & clip).volume < 1e-3, name
    bb, br = clip.bounding_box(), near["bracket1"].bounding_box()
    assert bb.max.Z > br.min.Z + DT.bracket_bar  # it reaches up past the bracket's bottom onto the legs
    wall_legs = [near["bay0_wall_arch_end"], near["bay1_wall_arch_start"]]
    assert all((Pos(0, 0, 0.1) * clip & leg).volume < 1e-3 for leg in wall_legs)  # slides up: nothing over the legs


@pytest.mark.parametrize("move", [(-1, 0), (1, 0), (0, -1), (0, 1)])
def test_clip_holds_the_legs_bottoms(joint, move):
    """Either leg pushed out along the track, or either leg sideways, by more than the fit hits the clip."""
    near, clip = joint
    d = DT.fit_pier + 0.05
    legs = {-1: near["bay0_wall_arch_end"], 1: near["bay1_wall_arch_start"]}
    sx, sy = move
    for side, leg in legs.items():
        if sx and sx != side:
            continue  # a leg pushed inward meets the bracket, not the clip
        moved = Pos(sx * d, sy * d, 0) * leg
        assert (moved & clip).volume > 1e-3, (side, move)


def test_clip_is_tight_on_the_legs():
    clip = leg_clip.make(DT)
    bb = clip.bounding_box()
    assert bb.size.Y == pytest.approx(leg_clip.leg_t(DT) + DT.fit_pier + 2 * DT.leg_clip_wall)
    assert bb.size.X == pytest.approx(2 * leg_clip.leg_reach(DT) + DT.fit_pier + 2 * DT.leg_clip_wall)
    assert bb.size.Z == pytest.approx(DT.leg_clip_floor + DT.bracket_bar + DT.leg_clip_grip)


def test_one_clip_per_bracket_between_bays():
    names = [n for n, _ in assembly.placed_parts(DT, [16 * INCH] * 3, (L.CORNER, L.CORNER))]
    assert sorted(n for n in names if n.startswith("leg_clip")) == ["leg_clip1", "leg_clip2"]
    arch = [n for n, _ in assembly.placed_parts(P, BAYS, (L.FREE, L.FREE))]
    assert not any(n.startswith("leg_clip") for n in arch)  # the arch's piers have their ribs there


# ---- the end clip: one leg, at a corner's rod anchor (the user, 2026-11-23) -------------------------------
@pytest.fixture(scope="module")
def corner_joint():
    """A deck-truss bay ending at the inside corner's first anchor (x = 0), and the end clip placed there."""
    from hotrain import corner_assembly as CA
    from hotrain import corner_layout as CL
    from hotrain.parts import arch_half
    b = BAYS[0]
    near = {n: s for n, s in CA.placed_parts(DT, CL.inside_corner())
            if s.bounding_box().min.X < 60 and s.bounding_box().max.X > -60}
    for y in DT.rail_ys:
        for start in (False, True):
            near[f"{'wall' if y == min(DT.rail_ys) else 'room'}_{'start' if start else 'end'}"] = (
                arch_half.place_half(DT, -b, b, y, start=start) * arch_half.make(DT, b, start=start))
    return near, leg_clip.place_end(DT, 0.0, -1) * leg_clip.make_end(DT)


def test_end_clip_prints_flat_in_one_piece():
    clip = leg_clip.make_end(DT)
    assert printable_problems(clip, DT) == []
    assert len(clip.solids()) == 1
    assert open_edges(clip) == 0
    assert off_layer_z(clip, DT.printer) == []
    bb = clip.bounding_box()
    w = DT.leg_clip_wall
    assert bb.size.X == pytest.approx(leg_clip.leg_reach(DT) + DT.fit_pier / 2 + w + (DT.bracket_t + DT.fit_slide) / 2 + w)
    assert bb.size.Y == pytest.approx(leg_clip.leg_t(DT) + DT.fit_pier + 2 * w)
    assert bb.size.Z == pytest.approx(DT.leg_clip_floor + DT.bracket_bar + DT.leg_clip_grip)


def test_end_clip_sits_under_the_anchor_touching_nothing(corner_joint):
    near, clip = corner_joint
    for name, shape in near.items():
        assert (shape & clip).volume < 1e-3, name
    anchor = near["anchor_in"]
    assert clip.bounding_box().max.Z > anchor.bounding_box().min.Z + DT.bracket_bar  # past the anchor's bottom bar
    assert clip.distance_to(anchor) < 1e-3  # its floor against the bar
    assert (Pos(0, 0, 0.1) * clip & near["wall_end"]).volume < 1e-3  # slides up: nothing over the leg


@pytest.mark.parametrize("move", [(-1, 0), (0, -1), (0, 1)])
def test_end_clip_holds_the_legs_bottom(corner_joint, move):
    """The leg pushed out along the track (away from the anchor) or sideways by more than the fit hits the clip."""
    near, clip = corner_joint
    d = DT.fit_pier + 0.05
    moved = Pos(move[0] * d, move[1] * d, 0) * near["wall_end"]
    assert (moved & clip).volume > 1e-3, move


def test_end_clip_hooks_the_anchor():
    """Its far wall is on the anchor's corner side: pulled by the leg, the clip meets the anchor."""
    from hotrain import corner_assembly as CA
    from hotrain import corner_layout as CL
    anchor = dict(CA.placed_parts(DT, CL.inside_corner()))["anchor_in"]
    clip = leg_clip.place_end(DT, 0.0, -1) * leg_clip.make_end(DT)
    assert (Pos(-(DT.fit_slide / 2 + 0.05), 0, 0) * clip & anchor).volume > 1e-3


def test_end_clip_turns_round_for_a_leg_on_the_other_side():
    a = leg_clip.place_end(DT, 0.0, -1) * leg_clip.make_end(DT)
    b = leg_clip.place_end(DT, 0.0, 1) * leg_clip.make_end(DT)
    ba, bb = a.bounding_box(), b.bounding_box()
    assert (ba.min.X, ba.max.X) == pytest.approx((-bb.max.X, -bb.min.X))
    assert (ba.min.Y, ba.max.Y, ba.min.Z) == pytest.approx((bb.min.Y, bb.max.Y, bb.min.Z))


def test_corner_kit_has_an_end_clip_per_rod_anchor():
    from hotrain import corner_layout as CL
    from hotrain import plates
    for c in (CL.inside_corner(), CL.bridge_corner()):
        names = [n for n, _ in plates.corner_kit(DT, c)]
        assert names.count("leg_clip_end") == sum(n.startswith("rod_anchor") for n in names) == 2
    assert not any(n == "leg_clip_end" for n, _ in plates.corner_kit(P, CL.inside_corner()))  # arch: ribs there
