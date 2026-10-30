"""A 3" sunflower in one go: flat back on the bed, no supports, yellow petals, a black disk, the brown ring of
spiral diamonds round the sunk black eye, hung plumb from a keyhole under the head; four to a plate."""
import json
import math
import zipfile

import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems, unsupported
from cadkit.mesh import Mesh
from cadkit.render import heights
from mini_sunflower import flower
from mini_sunflower.params import P

MN = (Align.CENTER, Align.CENTER, Align.MIN)


@pytest.fixture(scope="module")
def bodies():
    return flower.coloured(P)  # [(yellow, slot), (black, slot), (brown, slot)]


@pytest.fixture(scope="module")
def body():
    return flower.body(P)


def front_heights(meshes, step=0.25):
    r = P.diameter / 2 + 1
    return heights(meshes, ((-r, -r), (r, r)), step=step)


def at(grid, x, y, step=0.25):
    r = P.diameter / 2 + 1
    return grid[int(round((y + r) / step)), int(round((x + r) / step))]


def test_one_piece_flat_on_the_bed_three_inches_across(body):
    assert printable_problems(body.translate((P.printer.bed / 2, P.printer.bed / 2, 0)), P.printer) == []
    assert len(body.solids()) == 1 and open_edges(body) == 0
    bb = body.bounding_box()
    longest = max(bb.size.X, bb.size.Y)
    assert P.diameter * (1 - P.vary[0]) < longest <= P.diameter + 1e-3


def test_no_supports_needed(body):
    """Nothing overhangs past 45 degrees; the only face looking down is the keyhole's roof (a short bridge)."""
    assert all(z == pytest.approx(flower.key_top(P), abs=0.05) for z, a in overhangs(body) if a > 0.01)
    faces = downward_faces(body)
    assert faces and all(z == pytest.approx(flower.key_top(P), abs=0.05) for z, _ in faces)


def test_colours_by_height_yellow_black_brown(bodies, body):
    """Yellow up to black_z, the black disk to brown_z, brown above: two flat seams, each colour on the one below."""
    (yellow, ys), (black, ks), (brown, bs) = bodies
    assert (ys, ks, bs) == (P.slot_yellow, P.slot_black, P.slot_brown)
    assert yellow.bounding_box().max.Z == pytest.approx(P.black_z, abs=1e-4)
    assert black.bounding_box().min.Z == pytest.approx(P.black_z, abs=1e-4)
    assert black.bounding_box().max.Z == pytest.approx(P.brown_z, abs=1e-4)
    assert brown.bounding_box().min.Z == pytest.approx(P.brown_z, abs=1e-4)
    assert unsupported(black, yellow, probe=0.01) == pytest.approx(0, abs=0.05)
    assert unsupported(brown, black, probe=0.01) == pytest.approx(0, abs=0.05)
    assert sum(b.volume for b, _ in bodies) == pytest.approx(body.volume, rel=1e-3)
    for b, _ in bodies:
        assert open_edges(b) == 0
        assert off_layer_z(b, P.printer, min_area=0.01) == []


def test_from_the_front_a_sunk_black_eye_in_a_raised_brown_ring(bodies):
    (yellow, _), (black, _), (brown, _) = bodies
    k, b, y = front_heights([black]), front_heights([brown]), front_heights([yellow])
    eye = at(k, 0, 0)
    assert eye == pytest.approx(P.brown_z, abs=0.01) and np.isnan(at(b, 0, 0))  # black in the middle, nothing on it
    ring = np.nanmax(b)
    assert ring - P.brown_z >= max(h for _, h in P.brown)  # the brown stands up round the eye
    assert ring - np.nanmax(y) >= 3.0  # and well above the petals
    r_eye = min(r for r in np.arange(0, P.head_r, 0.1) if not np.isnan(at(b, r, 0)))
    assert r_eye == pytest.approx(P.eye_r, abs=0.3)


def test_brown_ring_has_the_spiral_diamonds():
    """Round a circle mid-ring, the top rises and falls the diamonds' height, once a seed."""
    r = 10.5
    th = np.linspace(0, 2 * np.pi, 4000, endpoint=False)
    z = flower.brown_top(P, np.full_like(th, r), th)
    assert np.ptp(z) == pytest.approx(P.texture, rel=0.15)
    bumps = ((z[1:-1] > z[:-2]) & (z[1:-1] >= z[2:]) & (z[1:-1] > z.min() + P.texture / 2)).sum()
    seeds_on_ring = 2 * np.pi * r / (P.seed_c * math.sqrt(math.pi))  # Vogel: a seed every c * sqrt(pi)
    assert bumps == pytest.approx(seeds_on_ring, rel=0.35)


def test_petals_two_rings_tip_to_tip():
    """Petal tips round the edge: 2 * petals of them, no two the same length, the front ring's shorter, in the
    back ring's gaps."""
    edge = [flower.reach(P, a) for a in np.arange(0, 360, 0.25)]
    tips = [i for i in range(len(edge)) if edge[i] > edge[i - 1] and edge[i] >= edge[(i + 1) % len(edge)]]
    assert len(tips) == 2 * P.petals
    assert max(edge) == pytest.approx(P.back.r1, abs=0.05)
    reach = sorted(edge[i] for i in tips)
    assert reach[0] >= P.front.r0 + (P.front.r1 - P.front.r0) * (1 - P.vary[0]) - 0.05
    assert reach[P.petals - 1] <= P.front.r1 + 0.05 < reach[P.petals]  # the front ring's tips, then the back's
    assert len({round(r, 2) for r in reach}) >= 2 * P.petals - 2


def test_keyhole_hangs_it_plumb_under_the_head(body):
    """The nail rests above the centre (straight above it: the flower is round), the keyhole wholly under the head
    with at least key_skin of solid between it and the front."""
    cavity = Mesh.union([Mesh.from_shape(s) for s in flower.keyhole(P)]) & flower.unkeyed(P)
    bb = cavity.bounding_box()
    assert math.hypot(max(abs(bb.min.X), abs(bb.max.X)), max(abs(bb.min.Y), abs(bb.max.Y))) < P.head_r
    probe = Mesh.from_shape(Pos(-0.05, 0, P.key_lip / 2) * Box(0.1, P.head_r, 0.1, align=(Align.MIN,) * 3))
    above = [s.bounding_box().min.Y for s in (body & probe).solids()]
    assert min(above) == pytest.approx(P.hang_y + flower.NAIL_D / 2, abs=0.05)
    air = Mesh.from_shape(Box(120, 120, 30, align=MN)) - flower.unkeyed(P)
    assert cavity.gap(air, 3.0) >= P.key_skin - 0.02


def test_hangs_plumb_from_the_nail(body):
    """No two petals are the same size, so the printed centre of mass (walls solid, the rest infill) isn't quite
    the centre: under the nail, it still hangs within a degree of upright."""
    _, (cx, cy, _) = body.printed(P.printer.layer)
    assert P.hang_y - cy > 5.0
    assert math.degrees(math.atan2(abs(cx), P.hang_y - cy)) < 1.0


def test_plate_four_flowers_round_the_tower_in_their_colours(tmp_path, body):
    settings = flower.write(P, tmp_path)
    s = slicers.active()
    objects = s.read_filaments(tmp_path / "plates" / f"mini_sunflowers{s.project_suffix}")
    assert len(objects) == P.per_plate
    for _, _, parts in objects:
        assert parts == {"flower_yellow": P.slot_yellow, "flower_black": P.slot_black, "flower_brown": P.slot_brown}
    x0, y0, x1, y1 = s.tower_keepout(settings)
    keepout = Mesh.from_shape(Pos(x0, y0, 0) * Box(x1 - x0, y1 - y0, 40, align=(Align.MIN,) * 3))
    for x, y in flower.spots(P):
        m = body.translate((x, y, 0))
        assert printable_problems(m, P.printer) == []
        assert (m & keepout).volume == 0
    cfg = json.loads(zipfile.ZipFile(tmp_path / "plates" / f"mini_sunflowers{s.project_suffix}")
                     .read("Metadata/project_settings.config"))
    assert cfg.get("enable_support", "0") == "0"


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_prints_yellow_then_black_then_brown(tmp_path):
    flower.write(P, tmp_path)
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"mini_sunflowers{s.project_suffix}", tmp_path / "s.3mf")
    bands = [f for f, _, _ in report["layers"] if f]
    assert bands == [(P.slot_yellow,), (P.slot_black,), (P.slot_brown,)]
    assert len(bands) - 1 == P.color_changes
    assert set(report["grams"]) == {P.slot_yellow, P.slot_black, P.slot_brown}
