"""Seed head: black body + brown seeds, one color change, sockets the pins snap into."""
import math

import pytest
from build123d import Compound

from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems, unsupported
from conftest import probe
from sunflower import layout
from sunflower.params import P
from sunflower.parts import center


def test_body_prints_flat_watertight_on_layers(head):
    body, seeds = head.children
    assert printable_problems(body, P.printer) == []
    assert open_edges(body) == 0
    assert off_layer_z(body, P.printer) == [] and off_layer_z(seeds, P.printer) == []


def test_seeds_start_on_the_body_one_color_change(head):
    body, seeds = head.children
    assert seeds.bounding_box().min.Z == pytest.approx(P.center_t)
    # every seed stands on the body's top: one whole disk at center_t (no socket breaks through), and the seeds
    # stay inside it (test_layout). cadkit.checks.unsupported proves the same but takes minutes on ~1,200 seeds.
    tops = [f for f in body.faces() if f.normal_at().Z > 1 - 1e-9 and f.center().Z == pytest.approx(P.center_t)]
    assert len(tops) == 1 and tops[0].area == pytest.approx(math.pi * P.center_r ** 2, rel=1e-6)
    sample = Compound(children=seeds.solids()[::50])
    assert unsupported(sample, body) == pytest.approx(0, abs=1e-6)
    assert len(seeds.solids()) == len(layout.seeds(P))
    assert (body.label, seeds.label) == ("center_black", "center_brown")


def test_rim_and_bevel(head):
    body = head.children[0]
    bb = body.bounding_box()
    assert bb.size.X == pytest.approx(2 * P.center_r, abs=0.05)
    c = bb.center()
    low = body & probe(c.X - 200, c.Y - 0.05, 0.1, 400, 0.1, 0.1)
    assert low.bounding_box().size.X == pytest.approx(2 * P.center_rb + 0.2, abs=0.2)


def _socket_widths(body, z):
    """Width of each socket at height z, probed radially in the assembly frame."""
    out = []
    c = body.bounding_box().center()
    from build123d import Pos, Rot
    for a in layout.pin_angles(P):
        line = Pos(c.X, c.Y, 0) * Rot(0, 0, a) * probe(P.pin_r - 8, -0.05, z, 16, 0.1, 0.1)
        b = sorted([(Rot(0, 0, -a) * Pos(-c.X, -c.Y, 0) * s).bounding_box() for s in (body & line).solids()],
                   key=lambda b: b.min.X)
        out.append(b[1].min.X - b[0].max.X)
    return out


def test_each_pin_gets_a_throat_and_a_wider_chamber(head):
    body = head.children[0]
    for w in _socket_widths(body, P.throat / 2):
        assert w == pytest.approx(P.pin_w + P.fit, abs=0.02)
    for w in _socket_widths(body, P.throat + 0.5):
        assert w == pytest.approx(P.pin_w + 2 * P.pin_barb + P.fit + 2 * center.CHAMBER_SPARE, abs=0.02)


def test_socket_roofs_are_tiny(head):
    faces = downward_faces(head.children[0])
    assert len(faces) == 8
    assert all(a < 3.0 for _, a in faces)
    assert max(z for z, _ in faces) < P.center_t - 1.0  # a floor of material above every socket
