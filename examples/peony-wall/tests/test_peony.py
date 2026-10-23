"""The whole peony: about 8" across, one solid flat on the bed, its fills hidden from the front, a yellow insert that
goes in from the back past nothing and can't go through, and a keyhole that takes the nail. Builds the flower
once per worker (about a minute): run with -n 2 at most."""
import math

import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, overhangs, printable_problems
from cadkit.render import heights
from peony_wall import flower, layout
from peony_wall.params import P

MIN = (Align.MIN, Align.MIN, Align.MIN)


def probe(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


@pytest.fixture(scope="module")
def peony():
    return flower.body(P)  # in the flower's frame: centre on the axis, back at z = 0


@pytest.fixture(scope="module")
def insert():
    return flower.insert(P)  # print orientation: its back on the bed


def test_one_solid_flat_on_the_bed_about_8_inches(peony):
    assert printable_problems(flower.make(P), P.printer) == []
    bb = peony.bounding_box()
    assert max(bb.size.X, bb.size.Y) == pytest.approx(P.diameter, abs=4.0)
    assert off_layer_z(peony, P.printer) == []


def test_the_fills_never_show_from_the_front(peony):
    """Looking straight at it on the wall, the flower with its fills is the flower without them: the fills sit under
    petals (their own, or the ones in front)."""
    r = P.diameter / 2 + 3
    bounds = ((-r, -r), (r, r))
    with_fill = heights([peony], bounds, step=0.5)
    bare = heights(flower.parts(P, fill_under=False), bounds, step=0.5)
    seen = ~np.isnan(bare)
    differ = (np.abs(np.nan_to_num(with_fill, nan=-9) - np.nan_to_num(bare, nan=-9)) > 0.5)
    assert differ.sum() / seen.sum() < 0.005  # a few cells along rim edges, where tessellations differ


def test_nothing_shows_the_wall_through_the_flower(peony):
    """No hole looks through to the wall: inside the guards' feet, every cell of the front view has flower (or the
    insert, in the middle) over it. (A keyhole's entry once cut through the thin floor beside its boss.)"""
    r = P.guard_foot
    h = heights([peony, flower.insert_placed(P)], ((-r, -r), (r, r)), step=0.5)
    ys, xs = np.mgrid[0:h.shape[0], 0:h.shape[1]]
    inside = np.hypot(xs * 0.5 - r, ys * 0.5 - r) < r - 2
    assert np.isnan(h[inside]).sum() == 0


def test_the_keyhole_boss_never_shows(peony):
    """The boss holding the keyhole sits under the bowl petals: the front view is the same without it."""
    r = P.diameter / 2 + 3
    bounds = ((-r, -r), (r, r))
    floor, ring, boss, *rest = flower.parts(P)
    with_boss, without = heights([floor, ring, boss] + rest, bounds, 0.5), heights([floor, ring] + rest, bounds, 0.5)
    assert (np.abs(np.nan_to_num(with_boss, nan=-9) - np.nan_to_num(without, nan=-9)) > 0.05).sum() == 0


def test_the_other_bodies_print_without_supports():
    """Each petal is checked in test_petals; the rest (floor, ring round the hole, keyhole boss) must be too."""
    for part in flower.structure(P):
        assert sum(a for _, a in overhangs(part, 47)) < 5.0


def test_only_some_of_the_yellow_shows(peony, insert):
    """The folded petals cover part of the stamens from the front, as in the photo, but not most of them."""
    r = P.hole_r + 2
    bounds = ((-r, -r), (r, r))
    alone = heights([flower.insert_placed(P)], bounds, step=0.5)
    both = heights([peony, flower.insert_placed(P)], bounds, step=0.5)
    yellow = ~np.isnan(alone)
    shows = yellow & (np.abs(np.nan_to_num(both) - np.nan_to_num(alone)) < 0.05)
    assert 0.3 < shows.sum() / yellow.sum() < 0.85


def test_insert_prints_flat_without_supports(insert):
    assert printable_problems(insert.translate((*flower.centre_xy(P), 0)), P.printer) == []
    assert sum(a for _, a in overhangs(insert, 47)) < 20.0  # the anthers' undersides, a fraction of a mm each


def test_insert_goes_in_from_the_back_and_stops(peony):
    """It slides in from behind (from below, as printed) touching nothing on the way, and the flare stops it."""
    placed = flower.insert_placed(P)
    assert placed.bounding_box().min.Z == pytest.approx(0, abs=1e-6)  # flush with the back: the wall holds it in
    for dz in (0.0, -2.0, -P.ring_t / 2, -P.ring_t - 1.0, -placed.bounding_box().max.Z):
        assert (peony & placed.translate((0, 0, dz))).volume < 1.0, dz
    assert (peony & placed.translate((0, 0, 0.6))).volume > 5.0  # pushed further, the flare hits the flower


def test_stamens_fit_through_the_hole(insert):
    """Every stamen tip stays inside the hole, or the insert couldn't pass through it from the back."""
    bb = insert.bounding_box()
    assert max(bb.size.X, bb.size.Y) / 2 <= P.hole_r + P.flare
    above = insert & probe(-50, -50, P.ring_t + 0.2, 100, 100, 50)  # above the plug's top
    abb = above.bounding_box()
    assert max(-abb.min.X, abb.max.X, -abb.min.Y, abb.max.Y) <= P.hole_r - P.fit_slide / 2


def test_keyhole_takes_the_nail_above_the_centre(peony):
    """The nail's shank rests against the top of the slot, key_at up +Y from the centre; the head sits under a
    lip with solid material over its roof, and the roof's strip is the flower's only bridge."""
    line = peony & probe(-0.05, P.key_at - 30, P.key_lip / 2, 0.1, 60, 0.1)
    above = [s.bounding_box() for s in line.solids() if s.bounding_box().min.Y > P.key_at - 1]
    top = min(b.min.Y for b in above)
    assert top - P.key_at == pytest.approx(flower.NAIL_D / 2, abs=0.05)
    assert P.key_boss_t - flower.key_top(P) >= 1.6 - 1e-9
    faces = downward_faces(peony)
    assert faces and all(z == pytest.approx(flower.key_top(P)) for z, _ in faces)


def test_plates_open_pink_and_yellow_with_no_supports(tmp_path):
    import json, zipfile
    from cadkit import slicers
    flower.write(P, tmp_path)
    s = slicers.active()
    for name, slot in (("peony", P.slot_flower), ("stamens", P.slot_insert)):
        path = tmp_path / "plates" / f"{name}{s.project_suffix}"
        assert [(n, f) for n, f, _ in s.read_filaments(path)] == [(name, slot)]
        cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
        assert cfg["enable_support"] == "0"


@pytest.mark.slow
def test_slicer_prints_both_plates_in_one_color_each(tmp_path):
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("needs a slicer")
    flower.write(P, tmp_path)
    for name, slot in (("peony", P.slot_flower), ("stamens", P.slot_insert)):
        report = s.slice_report(tmp_path / "plates" / f"{name}{s.project_suffix}", tmp_path / f"{name}.3mf")
        assert {f for r in report["layers"] for f in r[0]} == {slot}


@pytest.mark.slow
@pytest.mark.parametrize("i", range(len(layout.specs(P))))
def test_every_petal_prints_without_supports(i):
    from peony_wall import petals
    assert sum(a for _, a in overhangs(petals.local(P, layout.specs(P)[i]), 47)) < 25.0


def test_one_project_with_both_plates_and_an_assembled_one_to_look_at(tmp_path):
    """peony-wall: both prints in one Bambu project, a plate each (the file to share); peony_assembled: the flower
    with the insert in place, pink and yellow, to show what it makes (not to print: it would swap every layer)."""
    from cadkit import bambu3mf, slicers
    flower.write(P, tmp_path)
    s = slicers.active()
    both = tmp_path / "plates" / f"peony-wall{s.project_suffix}"
    assert [name for name, _ in bambu3mf.read_plates(both)] == ["peony", "stamens"]
    assert sorted((n, f) for n, f, _ in s.read_filaments(both)) == [("peony", P.slot_flower), ("stamens", P.slot_insert)]
    shown = tmp_path / "plates" / f"peony_assembled{s.project_suffix}"
    [(_, _, parts)] = s.read_filaments(shown)  # one object, a part per colour
    assert parts == {"peony": P.slot_flower, "stamens": P.slot_insert}
    assert len(bambu3mf.read_plates(shown)) == 1
