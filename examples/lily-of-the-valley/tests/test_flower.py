"""The whole sprig: one piece flat-back on the bed, no supports, green below the seam and white above it so that from
the front the bells are white and everything else green, hung plumb from a keyhole hidden under a bell."""
import json
import math
import zipfile

import numpy as np
import pytest

from build123d import Box, Pos

from cadkit import bambu, gcode, slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, overhangs, printable_problems
from cadkit.mesh import Mesh
from cadkit.render import heights
from lily_of_the_valley import flower, shapes, sprig
from lily_of_the_valley.params import P


@pytest.fixture(scope="module")
def body():
    return flower.body(P)


@pytest.fixture(scope="module")
def bodies():
    return flower.coloured(P)  # [(green, slot), (white, slot)]


def test_one_piece_flat_on_the_bed_the_size_of_the_last_flower(body):
    assert printable_problems(flower.make(P), P.printer) == []
    assert len(body.solids()) == 1 and open_edges(body) == 0
    assert body.bounding_box().size.Y == pytest.approx(P.height, abs=3.0)


def test_no_supports_needed(body):
    """Nothing overhangs past 45 degrees (but specks under a tenth of a millimetre square, where the union's
    surfaces cross); the only face looking down is the keyhole roof's top."""
    assert all(z == pytest.approx(flower.key_top(P), abs=0.05) for z, a in overhangs(body) if a > 0.01)
    faces = downward_faces(body)
    assert faces and all(z == pytest.approx(flower.key_top(P), abs=0.05) for z, _ in faces)


def test_green_below_the_seam_white_above_one_change(body, bodies):
    """A level cut through a body with no overhangs, so the white never starts over air (unsupported() would count
    the bells' 46-degree fills, which print fine)."""
    (green, gs), (white, ws) = bodies
    assert (gs, ws) == (P.slot_green, P.slot_white)
    assert green.volume + white.volume == pytest.approx(body.volume, rel=1e-4)
    assert green.bounding_box().max.Z == pytest.approx(P.seam, abs=1e-3)
    assert white.bounding_box().min.Z == pytest.approx(P.seam, abs=1e-3)
    for b in (green, white):
        assert off_layer_z(b, P.printer) == []


def test_from_the_front_the_bells_are_white_and_the_rest_green(body):
    """Straight on: wherever a bell is, what you see is above the seam (white); everywhere else (stem, pedicels,
    bracts) it's at or below it (green)."""
    bb = body.bounding_box()
    bounds = ((bb.min.X, bb.min.Y), (bb.max.X, bb.max.Y))
    seen = heights([body], bounds, step=0.4)
    bells = heights([sprig.placed_bell(P, k) for k in range(len(P.bells))], bounds, step=0.4)
    on_bell, off_bell = ~np.isnan(bells), np.isnan(bells) & ~np.isnan(seen)
    assert (seen[on_bell] > P.seam).mean() > 0.995  # a cell's corner at a bell's very edge may catch a pedicel
    assert (seen[off_bell] <= P.seam + 1e-3).all()
    assert off_bell.sum() > 0.25 * on_bell.sum()  # there is a green sprig to see


def test_every_bell_hangs_from_a_pedicel_off_the_stem():
    stem = sprig.stem(P)
    for k in range(len(P.bells)):
        ped, bell = sprig.pedicel(P, k), sprig.placed_bell(P, k)
        assert (ped & stem).volume > 0 and (ped & bell).volume > 0
        assert len(Mesh.union([stem, ped, bell]).solids()) == 1


def tilt(cx: float, cy: float) -> float:
    """Degrees off upright the sprig hangs, its printed mass centred at (cx, cy) under the nail."""
    hx, hy = flower.hang_point(P)
    assert hy - cy > 5.0  # the nail is above the centre of mass
    return math.degrees(math.atan2(abs(hx - cx), hy - cy))


def test_every_pedicel_stands_on_the_bed_two_lines_wide():
    """Narrower, and the slicer leaves the fill's foot out of the first layer: the pedicel's next layer starts over
    air (the pre-print review found each pedicel's first layer missing)."""
    for k in range(len(P.bells)):
        _, r, z = sprig.pedicel_sections(P, k)
        for rr, zz in zip(r, z):
            w, h, _ = shapes.section(rr, zz)
            assert np.ptp(w[h == 0]) >= 2 * P.printer.nozzle


def modulus_out(w: np.ndarray, z: np.ndarray) -> float:
    """A section's modulus (mm^3) bending out of the wall: about the level axis through its centroid."""
    w1, z1 = np.roll(w, -1), np.roll(z, -1)
    c = w * z1 - w1 * z
    a = c.sum() / 2
    zc = ((z + z1) * c).sum() / (6 * a)
    return (((z * z + z * z1 + z1 * z1) * c).sum() / 12 - a * zc * zc) / np.abs(z - zc).max()


def test_the_key_bells_pedicel_takes_a_knock_out_from_the_wall():
    """Everything hangs from the key bell, the rest reaching it through its pedicel. Knocked sideways in the wall's
    plane the sprig just turns on the nail; pulled straight out from the wall at its far end, that pedicel bends.
    At P.knock no section of it passes printed PLA's strength, taking it alone and the arm to the farthest point in
    plan (the review found 47 MPa at 1 N). The pedicel next below runs into the same bell, so it has about twice that.
    """
    far = flower.unkeyed(P).verts[:, :2]
    path, r, z = sprig.pedicel_sections(P, P.key_bell)
    stress = [P.knock * np.hypot(*(far - q).T).max() / modulus_out(*shapes.section(rr, zz)[:2])
              for q, rr, zz in zip(path, r, z)]
    assert max(stress) <= P.pla_strength


def test_keyhole_hangs_it_plumb_under_a_bell(body):
    hx, hy = flower.hang_point(P)
    _, (cx, cy, _) = body.printed(P.printer.layer)  # walls print solid, the bells' insides at infill
    assert tilt(cx, cy) < 1.0  # so it hangs within a degree of upright
    # the nail rests at the hang point: the slot's top is a nail's radius above it
    probe = Mesh.from_shape(flower.probe_up(P))
    above = [s.bounding_box() for s in (body & probe).solids() if s.bounding_box().min.Y > hy - 1]
    assert min(b.min.Y for b in above) == pytest.approx(hy + flower.NAIL_D / 2, abs=0.05)
    # and the keyhole is wholly inside the bell, a wall's thickness from the air all round (the mouth's hollow too)
    cavity = Mesh.union([Mesh.from_shape(s) for s in flower.keyhole(P)]) & flower.unkeyed(P)
    air = Mesh.from_shape(Pos(hx, hy, 0) * Box(60, 60, 30, align=flower.MN)) - flower.unkeyed(P)
    assert cavity.gap(air, 3 * P.key_wall) >= P.key_wall - 0.02


def test_plate_is_one_object_green_and_white_no_supports(tmp_path):
    flower.write(P, tmp_path)
    s = slicers.active()
    path = tmp_path / "plates" / f"lily_of_the_valley{s.project_suffix}"
    [(name, _, parts)] = s.read_filaments(path)
    assert name == "lily_of_the_valley"
    assert parts == {"sprig_green": P.slot_green, "sprig_white": P.slot_white}
    cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    assert cfg.get("enable_support", "0") == "0"


def test_prime_tower_clears_the_sprig():
    x, y, w = flower.tower(P)
    bb = flower.make(P).bounding_box()
    assert x + w < bb.min.X or x > bb.max.X or y + w < bb.min.Y or y > bb.max.Y
    assert 0 <= x and x + w <= P.printer.bed and 0 <= y


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_prints_green_then_white_with_one_change(tmp_path):
    flower.write(P, tmp_path)
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"lily_of_the_valley{s.project_suffix}", tmp_path / "s.3mf")
    bands = [f for f, _, _ in report["layers"] if f]  # bottom up; layers with nothing on them don't count
    assert bands == [(P.slot_green,), (P.slot_white,)]
    assert set(report["grams"]) == {P.slot_green, P.slot_white}
    # and what it lays down balances under the nail
    x, y, _ = gcode.centre_of_mass(bambu.plate_gcode(tmp_path / "s.3mf"))
    bx, by = flower.centre_xy(P)
    assert tilt(x - bx, y - by) < 1.0
