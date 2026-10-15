"""Snap pin: printed flat so the barb arms flex along the layers."""
import pytest

from cadkit.checks import off_layer_z, open_edges, printable_problems
from conftest import probe
from sunflower import layout
from sunflower.params import P


def test_pin_prints_flat_watertight_on_layers(snap):
    assert printable_problems(snap, P.printer) == []
    assert open_edges(snap) == 0
    assert off_layer_z(snap, P.printer) == []
    assert snap.bounding_box().size.Z == pytest.approx(P.pin_t)


def test_pin_length_head_and_barbs(snap):
    bb = snap.bounding_box()
    y = layout.pin_y(P)
    assert bb.size.Y == pytest.approx(y["tip"])
    assert bb.size.X == pytest.approx(P.pin_w + 2 * P.pin_lip)
    cx = bb.center().X
    at = lambda yy: sorted((s.bounding_box() for s in (snap & probe(cx - 10, yy - 0.05, 0.1, 20, 0.1, 0.1)).solids()),
                           key=lambda b: b.min.X)
    barb = at(y["barb"] + 0.05)
    assert len(barb) == 2  # split: two arms that flex inward
    assert barb[0].min.X == pytest.approx(cx - P.pin_w / 2 - P.pin_barb, abs=0.02)
    assert len(at(y["tip"] - P.pin_slot_len + 0.5)) == 2  # the split runs this far down
    assert len(at(y["head"] / 2)) == 1
    # the split ends in a half-round, not a square corner that concentrates the bending
    root = y["tip"] - P.pin_slot_len
    gap = lambda yy: (lambda b: b[1].min.X - b[0].max.X)(at(yy))
    assert gap(root + 0.15) < P.pin_slot_w / 2  # narrows toward the root
    assert gap(root + P.pin_slot_w / 2 + 0.1) == pytest.approx(P.pin_slot_w, abs=0.01)
