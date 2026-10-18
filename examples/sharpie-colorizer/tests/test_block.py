"""The marker block: prints upright unsupported, a straight clear channel guided past every felt window, sockets
that grip only the straight front section, tube sockets, and the slot for the clip's rail."""
import math

import pytest
from build123d import Align, Box, Cylinder, Plane, Pos, extrude

from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
from sharpie_colorizer.joints import rail_profile
from sharpie_colorizer.layout import channel_y, mouth_l, straight_from_tip, tip_point, top_z
from sharpie_colorizer.params import P
from sharpie_colorizer.parts import block

UP = (Align.CENTER, Align.CENTER, Align.MIN)
MARKERS = range(len(P.azimuths_deg))


@pytest.fixture(scope="module")
def part():
    return block.make_use(P)


def rod(r, l0, l1):
    return Pos(0, 0, l0) * Cylinder(r, l1 - l0, align=UP)


def test_prints_flat_watertight_unsupported():
    part = block.make(P)
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert downward_faces(part) == []
    assert overhangs(part) == []


def test_channel_clear_full_height(part):
    filament = Pos(0, channel_y(P), 0) * rod(P.filament_d / 2, 0, top_z(P))
    assert (part & filament).volume == pytest.approx(0, abs=1e-3)


@pytest.mark.parametrize("i", MARKERS)
def test_opposite_wall_guides_past_every_window(part, i):
    """Review Focus 1: a loading end the felt pushes aside rides the far wall, which is unbroken at the window."""
    phi = math.radians(P.azimuths_deg[i] + 180)
    r = P.channel_d / 2 + 0.15
    z0 = tip_point(P, i)[2]
    for dz in (-1.0, 0.0, 1.0, 2.0, 3.0):
        probe = Pos(r * math.cos(phi), channel_y(P) + r * math.sin(phi), z0 + dz) * Box(0.1, 0.1, 0.1)
        assert (part & probe).volume > 0, f"no wall opposite marker {i} at {dz:+} mm"


@pytest.mark.parametrize("i", MARKERS)
def test_marker_socket_grips_the_straight_section(part, i):
    frame = block.marker_frame(P, i)
    lo, hi = straight_from_tip(P, "long"), mouth_l(P)
    assert (part & frame * rod(P.marker_fit_d / 2 - 0.01, lo, hi)).volume == pytest.approx(0, abs=1e-3)
    assert (part & frame * rod(P.marker_fit_d / 2 + 0.2, lo, hi)).volume > 1


@pytest.mark.parametrize("i", MARKERS)
def test_nothing_past_the_mouth(part, i):
    ring = block.marker_frame(P, i) * rod(P.marker_body_d / 2 + 0.5, mouth_l(P) + 0.5, mouth_l(P) + 40)
    assert (part & ring).volume == pytest.approx(0, abs=1e-3)


@pytest.mark.parametrize("end", ["outlet", "inlet"])
def test_tube_sockets(part, end):
    z0 = 0 if end == "outlet" else top_z(P) - P.tube_depth
    at = Pos(0, channel_y(P), z0)
    assert (part & at * rod(P.tube_fit_d / 2 - 0.01, 0, P.tube_depth)).volume == pytest.approx(0, abs=1e-3)
    assert (part & at * rod(P.tube_fit_d / 2 + 0.3, 1, P.tube_depth - 1)).volume > 1


def test_outlet_mouth_chamfered(part):
    """Review Focus 5: elephant foot can't close the outlet on the bed face."""
    mouth = Pos(0, channel_y(P), 0.05) * rod(P.tube_fit_d / 2 + P.bed_chamfer / 2, 0, 0.1)
    assert (part & mouth).volume == pytest.approx(0, abs=1e-4)


def test_slot_takes_the_rail(part):
    rail = lambda c: Pos(-P.clip_w, 0, 0) * extrude(Plane.YZ * rail_profile(P, c), 2 * P.clip_w)
    assert (part & rail(0)).volume == pytest.approx(0, abs=1e-3)
    assert (part & rail(P.rail_clear + 0.1)).volume > 1


def test_inlet_socket_walls_off_every_marker_cavity():
    """Final review 1: 0.8 mm of plastic between the inlet funnel and every marker's cavity."""
    from sharpie_colorizer.joints import marker_cavity, tube_socket
    from build123d import Rot
    grown = Pos(0, channel_y(P), top_z(P)) * Rot(180, 0, 0) * tube_socket(P, fit_d=P.tube_fit_d + 1.6)
    for i in MARKERS:
        assert (grown & block.marker_frame(P, i) * marker_cavity(P)).volume == pytest.approx(0, abs=1e-6), i


def test_slot_mouth_chamfered_on_the_bed():
    """Final review 5: elephant foot can't bind the rail where the slot meets the bed."""
    from sharpie_colorizer.joints import rail_profile
    mouth = Pos(-P.clip_w, 0, 0.05) * extrude(Plane.YZ * rail_profile(P, P.rail_clear + P.bed_chamfer / 2), 2 * P.clip_w)
    assert (block.make_use(P) & (mouth & Pos(0, 0, 0.05) * Box(4 * P.clip_w, 40, 0.1))).volume == \
        pytest.approx(0, abs=1e-4)
