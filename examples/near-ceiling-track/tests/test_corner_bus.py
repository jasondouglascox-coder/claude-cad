"""The corner bus at track height (2026-11-07): it hung in hooks under the floor beams, in plain view under the
bridge. It now lies on each floor beam's top just outside the wall-side truss, behind the truss's solid band (skirt
and bottom chord), and drops into the anchors' wire notches, where the straight runs carry it."""
import pytest
from build123d import Align, Box, Pos

from hotrain import corner_assembly as A
from hotrain import corner_layout as C
from hotrain.params import P
from hotrain.parts import bow_frame, floor_beam
from hotrain.span_geom import span_geom


@pytest.fixture(scope="module", params=["inside", "bridge"])
def corner(request):
    c = C.inside_corner() if request.param == "inside" else C.bridge_corner()
    return c, A.placed_parts(P, c), A.bus(P, c)


def test_bus_lies_outside_the_wall_side_frames():
    """u < 0 is the wall side; the bus's room-side edge clears every wall-side frame's outer face."""
    out = P.bow_frame_y + P.bow_frame_t / 2 - span_geom(P, True).yc  # the curve spans' frames sit farther out
    assert floor_beam.bus_u(P) + P.bus_w / 2 <= -(out + P.corner_bus_clear) + 1e-9


def test_bus_rides_on_every_beam_top(corner):
    """At each portal between the anchors the bus rests on the beam (or portal bracket) under it."""
    c, items, bus = corner
    beams = [s for n, s in items if n.startswith(("floor_beam", "portal"))]
    wires = [s for _, s in bus]
    for i, pt in enumerate(C.portals(P, c)[1:-1], start=1):
        x, y = floor_beam.plan(P, pt, floor_beam.bus_u(P))
        on = Pos(x, y, 0.05) * Box(1, 1, 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        under = Pos(x, y, -0.25) * Box(1, 1, 0.2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        assert any((w & on).volume > 0 for w in wires), i
        assert any((b & under).volume > 0 for b in beams), i


def test_bus_stays_behind_the_trusses_solid_band(corner):
    """Between the end spans it never drops below the frames' skirt or rises above their bottom chord, so from the
    room the truss hides it; at the anchors it meets the straight runs' wire notch."""
    c, _, bus = corner
    top = P.tie_h + P.bow_chord_h
    ps = C.portals(P, c)
    ends = [(ps[0], ps[1]), (ps[-1], ps[-2])]
    for name, s in bus:
        bb = s.bounding_box()
        assert bb.max.Z <= top + 1e-6, name
        mid = bb.center()
        in_end_span = any(abs((mid.X - a.x) * (b.x - a.x) + (mid.Y - a.y) * (b.y - a.y)) < P.bow_span ** 2
                          for a, b in ends)
        if not in_end_span:
            assert bb.min.Z >= bow_frame.u_bottom(P) - 1e-6, name
        else:
            assert bb.min.Z >= P.bus_floor - 0.05, name  # down to the anchor's notch


def test_no_hooks_under_the_beams():
    for rods in (True, False):
        bb = floor_beam.make(P, rods=rods).bounding_box()
        assert bb.size.Y == pytest.approx(-floor_beam.bottom(P) + P.corner_bus_lip_h)  # beam depth plus the lip
