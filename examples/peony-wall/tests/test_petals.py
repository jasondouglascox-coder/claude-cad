"""Petals one at a time: the layout's numbers, the ruffle, the fit, and the 45-degree fill that lets every petal rest
on the one below with no supports, hidden from the front."""
import dataclasses

import numpy as np
import pytest

from cadkit.checks import open_edges, overhangs
from cadkit.render import heights
from peony_wall import layout, petals
from peony_wall.params import P

SPECS = layout.specs(P)
GUARDS = [s for s in SPECS if s.kind == "guard"]
BOWL = [s for s in SPECS if s.kind == "bowl"]
FOLDS = [s for s in SPECS if s.kind == "fold"]
# one of each kind, and the bowl's two ends and middle
SAMPLES = {"guard": GUARDS[0], "bowl_inner": BOWL[0], "bowl_middle": BOWL[len(BOWL) // 2], "bowl_outer": BOWL[-1],
           "fold": FOLDS[0]}


def test_layout_has_every_petal():
    assert (len(GUARDS), len(BOWL), len(FOLDS)) == (P.guards, P.bowl, len(P.folds))


def test_no_petal_leans_past_what_prints():
    """Out past lean_out_max a ruffle crest rolls over (its top faces down); in past lean_in_max a petal's own
    underside overhangs. Neither can be fixed by a fill underneath."""
    for s in SPECS:
        for lean in (s.lean0, s.lean):
            assert -P.lean_in_max <= lean <= P.lean_out_max, s


def test_bowl_curls_in_at_the_middle_and_leans_out_at_the_edge():
    assert BOWL[0].lean < 0 < BOWL[-1].lean
    assert BOWL[0].foot == pytest.approx(P.bowl_feet[0]) and BOWL[-1].foot == pytest.approx(P.bowl_feet[1])
    assert all(b.foot >= a.foot for a, b in zip(BOWL, BOWL[1:]))


def test_layout_is_repeatable_and_seeded():
    assert layout.specs(P) == SPECS
    assert layout.specs(dataclasses.replace(P, seed=P.seed + 1)) != SPECS


def test_ruffle_is_flat_at_the_foot_and_full_at_the_rim():
    s = SAMPLES["bowl_middle"]
    ruffled, _ = petals.grid(P, s)
    flat, _ = petals.grid(P, dataclasses.replace(s, amp=0.0))
    moved = np.linalg.norm(ruffled - flat, axis=2)
    assert moved[:, 0].max() < 1e-9
    assert moved[:, -1].max() == pytest.approx(s.amp, rel=0.15)


@pytest.mark.parametrize("name", SAMPLES)
def test_petal_is_a_solid_standing_on_the_bed(name):
    part = petals.local(P, SAMPLES[name])
    assert part.is_valid and len(part.solids()) == 1 and open_edges(part) == 0
    assert part.bounding_box().min.Z == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("name", SAMPLES)
def test_petal_prints_without_supports(name):
    """Nothing faces down past what prints: under 25 mm2 past 47 degrees (facets of the 45-degree fill), against
    thousands for the bare petal."""
    s = SAMPLES[name]
    assert sum(a for _, a in overhangs(petals.local(P, s), 47)) < 25.0


@pytest.mark.parametrize("name", ["guard", "bowl_outer"])
def test_the_fill_stays_under_its_petal(name):
    """Looking straight at the wall you see the petal's top face: wherever its top skin is, the filled petal's top
    is that skin. (Beside a narrow claw the fill can reach past the petal's outline; the whole flower's front view,
    in test_peony, shows that the petals in front hide it.)"""
    s = SAMPLES[name]
    bb = petals.local(P, s).bounding_box()
    bounds = ((bb.min.X - 1, bb.min.Y - 1), (bb.max.X + 1, bb.max.Y + 1))
    filled = heights([petals.local(P, s)], bounds, step=0.5)
    top = heights([petals.local(P, s, fill_under=False)], bounds, step=0.5)  # just the wall: its top is the skin
    seen = ~np.isnan(top)
    assert seen.sum() > 1000
    off = np.abs(filled[seen] - top[seen]) > 0.3
    assert off.sum() / seen.sum() < 0.01  # a few cells at the rim's edge
