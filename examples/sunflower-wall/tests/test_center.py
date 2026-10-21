"""Seed head: a thin black floor out to the rim, brown seeds on it, one color change."""
import math

import pytest
from build123d import Compound, Pos

from cadkit.checks import off_layer_z, open_edges, printable_problems, unsupported
from sunflower import flower, layout
from sunflower.parts import center

S = flower.params()


@pytest.fixture(scope="module")
def head():
    return center.assembled(S)


def test_body_prints_flat_watertight_on_layers(head):
    body, seeds = head.children
    assert printable_problems(Pos(S.center_r, S.center_r, 0) * body, S.printer) == []  # moved onto the bed
    assert open_edges(body) == 0
    assert off_layer_z(body, S.printer) == [] and off_layer_z(seeds, S.printer) == []


def test_seeds_start_on_the_floor_one_color_change(head):
    body, seeds = head.children
    assert seeds.bounding_box().min.Z == pytest.approx(S.center_t)
    tops = [f for f in body.faces() if f.normal_at().Z > 1 - 1e-9 and f.center().Z == pytest.approx(S.center_t)]
    assert len(tops) == 1 and tops[0].area == pytest.approx(math.pi * S.center_r ** 2, rel=1e-6)
    sample = Compound(children=seeds.solids()[::50])
    assert unsupported(sample, body) == pytest.approx(0, abs=1e-6)
    assert len(seeds.solids()) == len(layout.seeds(S))
    assert (body.label, seeds.label) == ("center_black", "center_brown")


def test_floor_runs_out_to_the_rim(head):
    bb = head.children[0].bounding_box()
    assert bb.size.X == pytest.approx(2 * S.center_r, abs=0.05) and bb.size.Z == pytest.approx(S.center_t)
