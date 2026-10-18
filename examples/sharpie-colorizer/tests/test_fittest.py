"""The fit-test plate: every piece prints unsupported, every variant is the size it claims and is numbered."""
import math

import pytest
from build123d import Align, Box, Cylinder, Location, Pos, RectangleRounded, extrude

from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
from sharpie_colorizer.parts.fittest import (bar_center, bore_axis, clip_slice, fit_items, marker_strip,
                                             tube_hole, tube_strip)
from sharpie_colorizer.params import P

UP = (Align.CENTER, Align.CENTER, Align.MIN)
ITEMS = dict(fit_items(P))


@pytest.mark.parametrize("name", list(ITEMS))
def test_prints_flat_watertight_unsupported(name):
    part = ITEMS[name]
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert downward_faces(part) == []
    assert overhangs(part) == []


def along(origin, direction, r, l0, l1):
    """A rod of radius r on the line origin + l·direction, from l0 to l1."""
    dx, dy, dz = direction
    tilt = math.degrees(math.acos(dz))
    yaw = math.degrees(math.atan2(dy, dx))
    loc = Location(origin) * Location((0, 0, 0), (0, 0, 1), yaw) * Location((0, 0, 0), (0, 1, 0), tilt)
    return loc * (Pos(0, 0, l0) * Cylinder(r, l1 - l0, align=UP))


@pytest.mark.parametrize("k", range(len(P.marker_fits)))
def test_marker_strip_bore_k_is_its_size(k):
    strip, (o, d), fit = marker_strip(P), bore_axis(P, k), P.marker_fits[k]
    inside = P.fit_h / d[2]  # axis length between the bed and the top
    assert (strip & along(o, d, fit / 2 - 0.01, 0, inside)).volume == pytest.approx(0, abs=1e-3)
    assert (strip & along(o, d, fit / 2 + 0.1, 0.3 * inside, 0.7 * inside)).volume > 0.1


@pytest.mark.parametrize("k", range(len(P.tube_fits)))
def test_tube_strip_hole_k_is_its_size(k):
    strip, (x, y), fit = tube_strip(P), tube_hole(P, k), P.tube_fits[k]
    h = strip.bounding_box().max.Z
    assert (strip & Pos(x, y, 0) * Cylinder(fit / 2 - 0.01, h, align=UP)).volume == pytest.approx(0, abs=1e-3)
    assert (strip & Pos(x, y, 2) * Cylinder(fit / 2 + 0.1, h - 4, align=UP)).volume > 0.1


def test_tube_strip_bed_mouths_chamfered():
    strip, (x, y) = tube_strip(P), tube_hole(P, 0)
    assert (strip & Pos(x, y, 0) * Cylinder(P.tube_fits[0] / 2 + P.bed_chamfer - 0.05, 0.02, align=UP)).volume == \
        pytest.approx(0, abs=1e-4)


@pytest.mark.parametrize("k", range(len(P.hooks)))
def test_clip_slice_holds_the_bar(k):
    s = clip_slice(P, k)
    bar = Pos(*bar_center(P), 0) * extrude(RectangleRounded(P.bar_w, P.bar_h, P.bar_r), 8)
    assert (s & bar).volume == pytest.approx(0, abs=1e-3)
    assert (s & Pos(0, -1, 0) * bar).volume > 0.1  # pulled off: the lips catch the bar


def bars_on_top(part):
    """Count the raised marks: separate solids in a thin slab just under the part's top."""
    bb = part.bounding_box()
    slab = Pos(bb.min.X - 1, bb.min.Y - 1, bb.max.Z - 0.1) * Box(bb.size.X + 2, bb.size.Y + 2, 0.05,
                                                                 align=(Align.MIN,) * 3)
    return len((part & slab).solids())


def test_every_variant_is_numbered():
    assert bars_on_top(marker_strip(P)) == sum(range(1, len(P.marker_fits) + 1))
    assert bars_on_top(tube_strip(P)) == sum(range(1, len(P.tube_fits) + 1))
    assert [bars_on_top(clip_slice(P, k)) for k in range(len(P.hooks))] == [1, 2, 3]
