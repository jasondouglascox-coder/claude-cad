"""The whole lily: about 180 mm across, one piece flat on the bed, white and purple bodies that split it exactly by
layers, white tips and margins with purple hearts, a keyhole at the centre, a plate with tree supports in the
loaded PLA (a PETG interface cost 110 swaps and 9.8 h)."""
import math

import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from lily_wall import colour, flower, tepals
from lily_wall.params import P

MIN = (Align.MIN, Align.MIN, Align.MIN)


def probe(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


@pytest.fixture(scope="module")
def lily():
    return flower.body(P)


@pytest.fixture(scope="module")
def bodies():
    return flower.coloured(P)  # [(white mesh, slot), (purple mesh, slot)] in the flower's frame


def test_one_piece_flat_on_the_bed_about_180_mm(lily):
    assert printable_problems(flower.make(P), P.printer) == []
    bb = lily.bounding_box()
    assert max(bb.size.X, bb.size.Y) == pytest.approx(P.diameter, abs=4.0)
    assert open_edges(lily) == 0


def test_white_and_purple_split_it_exactly_by_layers(lily, bodies):
    (white, ws), (purple, ps) = bodies
    assert (ws, ps) == (P.slot_white, P.slot_purple)
    assert white.volume + purple.volume == pytest.approx(lily.volume, rel=1e-4)
    assert (white & purple).volume < 1e-3 * lily.volume
    for b in (white, purple):
        assert off_layer_z(b, P.printer) == []  # every colour seam on a layer boundary
    lo, hi = colour.band(P)
    assert purple.bounding_box().min.Z == pytest.approx(lo + P.printer.layer * colour.pattern(P).index(1), abs=1e-3)
    assert (white & probe(-200, -200, hi, 400, 400, 200)).volume == 0  # nothing white above the fade


def test_tips_and_margins_white_hearts_purple(bodies):
    """On every tepal: its tip and a margin at its widest are white; its midrib where it's highest is purple."""
    (white, _), (purple, _) = bodies
    for k in range(P.tepals):
        pts = tepals.placed_grid(P, k)
        mid = pts[pts.shape[0] // 2]
        peak = int(np.argmax(mid[:, 2]))
        for at, body in ((mid[-3], white), (pts[1, peak], white), (mid[peak], purple)):
            x, y, z = at
            assert (body & probe(x - 0.6, y - 0.6, z - 1.2, 1.2, 1.2, 1.2)).volume > 0, (k, at)


def test_keyhole_hangs_it_by_its_centre(lily):
    line = lily & probe(-0.05, -30, P.key_lip / 2, 0.1, 60, 0.1)
    above = [s.bounding_box() for s in line.solids() if s.bounding_box().min.Y > -1]
    assert min(b.min.Y for b in above) == pytest.approx(flower.NAIL_D / 2, abs=0.05)
    assert P.boss_t - flower.key_top(P) >= 1.6 - 1e-9
    faces = downward_faces(lily)
    assert faces and all(z == pytest.approx(flower.key_top(P)) for z, _ in faces)


def test_plate_is_one_object_in_two_colours_with_supports_in_the_same_pla(tmp_path):
    import json, zipfile
    from cadkit import slicers
    flower.write(P, tmp_path)
    s = slicers.active()
    path = tmp_path / "plates" / f"lily{s.project_suffix}"
    [(name, _, parts)] = s.read_filaments(path)
    assert name == "lily" and parts == {"lily_white": P.slot_white, "lily_purple": P.slot_purple}
    cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    assert cfg["enable_support"] == "1" and cfg["support_type"] == "tree(auto)"
    assert cfg["support_filament"] == "0"  # the trees in whatever's loaded: no swaps of their own
    assert cfg["support_interface_filament"] == "0"  # and their interface: no PETG swaps
    # PLA on PLA bonds: a layer's gap top and bottom so they snap off (the marks are on the undersides, at the wall)
    assert cfg["support_top_z_distance"] == str(P.printer.layer)
    assert cfg["support_bottom_z_distance"] == str(P.printer.layer)
    x, y, w = float(cfg["wipe_tower_x"][0]), float(cfg["wipe_tower_y"][0]), float(cfg["prime_tower_width"])
    cx, cy = flower.centre_xy(P)
    lb = flower.make(P).bounding_box()
    clear = x + w <= lb.min.X - 3 or y + w <= lb.min.Y - 3 or x >= lb.max.X + 3 or y >= lb.max.Y + 3
    assert clear  # the prime tower clears the lily's box


@pytest.mark.slow
def test_slicer_prints_it_white_then_purple_with_just_the_fades_changes(tmp_path):
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("needs a slicer")
    flower.write(P, tmp_path)
    report = s.slice_report(tmp_path / "plates" / f"lily{s.project_suffix}", tmp_path / "s.3mf")
    layers = report["layers"]
    assert {f for r in layers for f in r[0]} == {P.slot_white, P.slot_purple}
    assert all(len(f) == 1 for f, _, _ in layers)  # one colour a layer, supports included
    swaps = sum(a[0] != b[0] for a, b in zip(layers, layers[1:]))
    assert swaps == colour.changes(P)
