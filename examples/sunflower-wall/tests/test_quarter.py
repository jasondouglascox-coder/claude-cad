"""Petal quarters: print flat with no supports, slots and keyhole sized from params, petals uncut by the seams."""
import math

import pytest
from build123d import Align, Cylinder, Location, Pos, Rot

from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from conftest import probe
from sunflower import layout
from sunflower.params import P
from sunflower.parts import quarter


@pytest.mark.parametrize("layer", ["back", "front"])
def test_quarter_prints_flat_watertight_on_layers(layer, back, front):
    part = back if layer == "back" else front
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []


def test_back_quarter_stays_under_the_front_ring(back):
    assert back.bounding_box().max.Z == pytest.approx(P.back_t)


def test_only_downward_faces_are_the_pin_head_ledges(back, front):
    ledge = (P.pin_lip + P.fit / 2) * (P.pin_t + P.fit)
    faces = downward_faces(back)
    assert len(faces) == 2 * 2  # two pins, a ledge each side of the shank
    assert all(z == pytest.approx(P.pin_head) and a <= ledge + 1e-6 for z, a in faces)
    assert downward_faces(front) == []


def _asm(layer, part):
    """Quarter 0 back in the assembly frame, at its own z = 0."""
    return Pos(0, 0, -quarter.base_z(P, layer)) * (quarter.place(P, layer, 0) * part)


def _pins_in(layer):
    return [a for a in layout.pin_angles(P) if layout.in_quarter(a, layout.boundaries(P, layer)[0])]


@pytest.mark.parametrize("layer", ["back", "front"])
def test_pin_slots_are_shank_plus_fit(layer, back, front):
    part = _asm(layer, back if layer == "back" else front)
    z = P.pin_head + 0.5 if layer == "back" else P.front_t / 2
    for a in _pins_in(layer):
        # radial probe through the slot: the gap is the shank width plus the fit
        line = Rot(0, 0, a) * probe(P.pin_r - 10, -0.05, z, 20, 0.1, 0.1)
        ends = sorted([(Rot(0, 0, -a) * s).bounding_box() for s in (part & line).solids()], key=lambda b: b.min.X)
        assert len(ends) == 2
        assert ends[1].min.X - ends[0].max.X == pytest.approx(P.pin_w + P.fit, abs=0.02)


def test_keyhole_holds_a_screw_head_under_its_lip(back):
    part = _asm("back", back)
    a = layout.back_start(P) + 45
    r_in, r_top = P.key_r
    def width(r, z):
        line = Rot(0, 0, a) * Pos(r, 0, 0) * Rot(0, 0, 90) * probe(-15, -0.05, z, 30, 0.1, 0.1)
        b = sorted([(Rot(0, 0, -a) * s).bounding_box() for s in (part & line).solids()], key=lambda b: b.min.Y)
        return b[1].min.Y - b[0].max.Y
    mid = (r_in + r_top) / 2
    assert width(mid, P.key_lip / 2) == pytest.approx(P.key_shank_w, abs=0.05)  # lip holds the head
    assert width(mid, (P.key_lip + P.back_t) / 2) == pytest.approx(P.key_head_d, abs=0.05)  # head slides above it
    assert width(r_in, P.key_lip / 2) == pytest.approx(P.key_head_d, abs=0.05)  # round entry through the lip


@pytest.mark.parametrize("layer", ["back", "front"])
def test_seams_never_cut_a_visible_petal(layer, back, front):
    """Outside the seed head, a quarter is exactly its petals: the wedge cut only trims the hidden hub."""
    part = _asm(layer, back if layer == "back" else front)
    ring = Cylinder(400, 50, align=(Align.CENTER, Align.CENTER, Align.MIN)) - \
        Cylinder(P.center_r, 50, align=(Align.CENTER, Align.CENTER, Align.MIN))
    one = quarter.petal(P, layer) & ring
    assert (part & ring).volume == pytest.approx(P.petals // 4 * one.volume, rel=1e-4)


@pytest.mark.parametrize("layer", ["back", "front"])
def test_petal_is_never_thinner_than_the_minimum(layer):
    pet = quarter.petal(P, layer)
    ring = P.back if layer == "back" else P.front
    for r in (ring.r0 + 5, (ring.r0 + ring.r1) / 2, ring.r1 - 5):
        hw = layout.half_width(ring, r)
        for y in (0, 0.9 * hw):
            col = pet & probe(r - 0.05, y - 0.05, 0, 0.1, 0.1, 20)
            assert col.bounding_box().max.Z >= P.petal_min - 1e-6


def test_printed_petal_keeps_its_vein_grooves():
    """The solid, not just the math: a spline through the cross sections once smoothed the grooves away."""
    import numpy as np
    pet = quarter.petal(P, "front")
    r = (P.front.r0 + P.front.r1) / 2
    hw = layout.half_width(P.front, r)
    zs = []
    for y in np.linspace(-0.8 * hw, 0.8 * hw, 45):  # ~5 samples per groove
        zs.append((pet & probe(r - 0.05, y - 0.05, 0, 0.1, 0.1, 20)).bounding_box().max.Z)
    dips = sum(1 for a, b, c in zip(zs, zs[1:], zs[2:]) if b < a - 0.02 and b < c - 0.02)
    assert dips >= P.petal_veins - 3  # the outer grooves sit past 0.8 of the half width
