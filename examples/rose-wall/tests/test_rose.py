"""The rose: about 8" across, one solid flat on the bed, curved petals with pointed tips, a funnel centre that needs
no supports, PETG-interface supports under the curled outer petals only, and a keyhole that hangs it by its
centre."""
import math

import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, overhangs, printable_problems
from rose_wall import flower, petals
from rose_wall.params import P

MIN = (Align.MIN, Align.MIN, Align.MIN)


def probe(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


def test_petal_sides_rise_upright_then_lean_out_to_their_tip():
    line = petals.side(30.0, 120.0, P.bend)
    assert line[0][2] == 0 and math.degrees(line[1][2]) < 2.0  # starts upright
    assert math.degrees(line[-1][2]) == pytest.approx(120.0)
    assert all(b[2] >= a[2] for a, b in zip(line, line[1:]))  # the lean only grows: it curves out, never back in
    assert math.hypot(line[-1][0], line[-1][1]) < 30.0  # bent, so the tip is nearer the foot than the length


def test_only_the_outer_petals_curl_past_45_degrees():
    """The centre and the innermost outer petals print without supports; the curl is the outer petals'."""
    assert P.centre_lean[1] + P.centre_lip <= 45.0 and P.centre_lean[0] + P.centre_lip <= 45.0
    assert P.lean[0] <= 45.0 < P.lean[1]


def test_centre_is_a_funnel():
    """Centre petal rims step down toward the middle: you look down into it, like a real rose."""
    rims = []
    for k in range(P.centre_petals):
        g = k / (P.centre_petals - 1)
        line = petals.side(P.centre_top - P.centre_drop * (1 - g), petals.lerp(P.centre_lean, g), 1.6, P.centre_lip)
        rims.append(line[-1][1])
    assert all(b > a for a, b in zip(rims, rims[1:]))
    assert rims[-1] - rims[0] >= P.centre_drop * 0.9


def test_centre_petals_never_touch():
    """A gap between neighbouring centre petals' feet: the dark lines of the funnel."""
    for k in range(P.centre_petals - 1):
        assert petals.centre_foot(P, k + 1) - (petals.centre_foot(P, k) + P.wall) == pytest.approx(P.centre_gap)
    assert petals.outer_foot(P, 0) == pytest.approx(P.centre_r)


@pytest.mark.parametrize("k", [0, P.centre_petals - 1])
def test_centre_petals_print_without_supports(k):
    assert overhangs(petals.centre(P, k)) == []


@pytest.fixture(scope="module")
def rose():
    return flower.make(P)


def test_one_solid_flat_on_the_bed_about_8_inches(rose):
    assert printable_problems(rose, P.printer) == []
    bb = rose.bounding_box()
    assert max(bb.size.X, bb.size.Y) == pytest.approx(P.diameter, abs=4.0)
    assert off_layer_z(rose, P.printer) == []


def test_keyhole_hangs_it_by_its_centre(rose):
    """The nail's shank rests against the top of the slot, at the flower's centre; the head sits under a lip with
    solid material over its roof."""
    cx, cy = flower.centre_xy(P)
    line = rose & probe(cx - 0.05, cy - 30, P.key_lip / 2, 0.1, 60, 0.1)
    above = [s.bounding_box() for s in line.solids() if s.bounding_box().min.Y > cy - 1]
    top = min(b.min.Y for b in above)  # the first material above the slot
    assert top - cy == pytest.approx(flower.NAIL_D / 2, abs=0.05)
    assert P.base_t - flower.key_top(P) >= 1.6  # roof over the nail head
    faces = downward_faces(rose)
    assert faces and all(z == pytest.approx(flower.key_top(P)) for z, _ in faces)  # the only bridge: the roof's strip


def test_plate_opens_red_with_petg_supports(tmp_path):
    import json, zipfile
    from cadkit import slicers
    flower.write(P, tmp_path)
    s = slicers.active()
    path = tmp_path / "plates" / f"rose{s.project_suffix}"
    assert [(n, f) for n, f, _ in s.read_filaments(path)] == [("rose", P.slot_rose)]
    cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    assert cfg["enable_support"] == "1" and cfg["support_interface_filament"] == str(P.slot_support)
    assert cfg["filament_type"][P.slot_support - 1] == "PETG"


@pytest.mark.slow
def test_slicer_supports_the_curls_with_petg(tmp_path):
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("needs a slicer")
    flower.write(P, tmp_path)
    report = s.slice_report(tmp_path / "plates" / f"rose{s.project_suffix}", tmp_path / "s.3mf")
    used = {f for r in report["layers"] for f in r[0]}
    assert used == {P.slot_rose, P.slot_support}
    assert report["grams"][P.slot_support] < report["grams"][P.slot_rose] / 5  # PETG only at the interface
