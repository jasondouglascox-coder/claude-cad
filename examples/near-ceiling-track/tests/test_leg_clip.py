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
