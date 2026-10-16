"""The 10-inch flower printed in one go: every part stacked in place on one plate, colors by height (yellow with
orange beads, then black, then brown),
nothing over air, and a keyhole that hangs it centered in the user's wall gap."""
import math

import pytest
from build123d import Axis, Compound, extrude

from cadkit.checks import downward_faces, off_layer_z, printable_problems, unsupported
from conftest import probe
from sunflower import small
from sunflower.params import P

S = small.params()


@pytest.fixture(scope="module")
def piece():
    return small.make(S)


def test_biggest_flower_the_bed_takes_with_the_same_thicknesses():
    assert P.printer.usable - 2 <= S.diameter <= P.printer.usable
    assert S.front.profile[-1][1] == P.front.profile[-1][1] and S.back_t == P.back_t and S.petal_min == P.petal_min
    assert S.center_r - S.center_rb == pytest.approx(S.center_t)  # 45-degree bevel
    assert P.printer.on_layer(S.center_t) and P.printer.on_layer(S.seed_dome)


def test_nail_height_comes_from_the_wall_measurements():
    """Centered in a 20 3/8" gap with the nail 8" below its top: the nail is 2 3/16" above the center."""
    assert small.NAIL_ABOVE_CENTER == pytest.approx((20.375 / 2 - 8) * 25.4)


def test_prints_flat_on_the_bed_in_colors_by_height(piece):
    yellow, orange, black, brown = piece.children
    assert printable_problems(yellow, S.printer) == []
    assert [b.label for b in piece.children] == ["flower_yellow", "flower_orange", "flower_black", "flower_brown"]
    for b in piece.children:
        assert off_layer_z(b, S.printer) == []
    assert black.bounding_box().min.Z == pytest.approx(yellow.bounding_box().max.Z)  # one change to black
    assert brown.bounding_box().min.Z == pytest.approx(black.bounding_box().max.Z)  # one change to brown
    # the black's footprint sits on yellow; the bevel above it climbs out at 45 degrees (checked in the first test),
    # which unsupported() would count as over air
    footprint = extrude(black.faces().sort_by(Axis.Z)[0], S.printer.layer)
    assert unsupported(footprint, yellow) == pytest.approx(0, abs=1e-6)
    assert unsupported(Compound(children=brown.solids()[::40]), black) == pytest.approx(0, abs=1e-6)


def test_nothing_starts_over_air(piece):
    """Front petals are filled down to the bed and the riser flares out from the hub; the only roof is the keyhole's
    top strip, a bridge as wide as the 45-degree roof leaves it."""
    roof = small._layer(S, S.key_head_d / 2 - small.ROOF_LEFT / 2)
    top_z = S.key_lip + small.KEY_HEAD_ROOM + roof
    w = S.key_head_d - 2 * roof
    assert 0 < w <= 1.0  # a bridge under a millimetre
    faces = downward_faces(piece.children[0])
    assert faces and all(z == pytest.approx(top_z) for z, _ in faces), faces
    assert sum(a for _, a in faces) <= small.KEY_LEN * w + math.pi * (w / 2) ** 2 + 1e-3
    black = piece.children[2]  # its only underside is its footprint, on the riser (previous test)
    assert [z for z, _ in downward_faces(black)] == [pytest.approx(small.riser_top(S))]
    assert downward_faces(piece.children[1]) == []


def test_orange_beads_down_the_front_petals_under_the_black(piece):
    """The 16-inch beads, scaled along the petal: they share layers with yellow only, and sit on it."""
    from build123d import Pos
    from sunflower.parts import quarter
    yellow, orange, black, _ = piece.children
    assert len(orange.solids()) == S.petals * len(S.bead_valleys)
    assert orange.volume == pytest.approx(S.petals * quarter.beads(S).volume, rel=1e-4)
    assert orange.bounding_box().max.Z < black.bounding_box().min.Z
    assert (orange & yellow).volume == pytest.approx(0, abs=1e-3)
    assert (Pos(0, 0, -0.1) * orange - yellow - orange).volume == pytest.approx(0, abs=1e-3)  # yellow under every bead


def test_prime_tower_fits_in_a_bed_corner_clear_of_the_flower():
    """The flower fills the bed; Bambu won't slice with its tower overlapping it."""
    x, y, w = small.tower(S)
    cx, cy = small.bed_center(S)
    near = math.hypot(cx - (x + w + small.TOWER_BRIM), cy - (y + w + small.TOWER_BRIM))
    assert near >= S.diameter / 2 + 1 and min(x, y) - small.TOWER_BRIM >= 0


def _axis_probe(piece, z):
    """Material along the keyhole axis, outward from the flower's center, at height z."""
    from build123d import Pos, Rot
    cx, cy = small.center_xy(S)
    line = Pos(cx, cy, 0) * Rot(0, 0, small.key_angle(S)) * probe(0, -0.05, z, S.diameter / 2, 0.1, 0.1)
    back = Rot(0, 0, -small.key_angle(S)) * Pos(-cx, -cy, 0)
    return sorted([(back * s).bounding_box() for s in (piece.children[0] & line).solids()], key=lambda b: b.min.X)


def test_hung_on_the_nail_the_flower_is_centered(piece):
    """The nail's shank rests against the top of the keyhole slot, NAIL_ABOVE_CENTER above the center."""
    pieces = _axis_probe(piece, S.key_lip / 2)
    top = next(b.min.X for b in pieces if b.min.X > 20)  # first material past the slot
    assert top == pytest.approx(small.NAIL_ABOVE_CENTER + small.NAIL_D / 2, abs=0.05)


def test_keyhole_holds_the_nail_head_under_the_lip_and_stays_hidden(piece):
    r_end = small.NAIL_ABOVE_CENTER - (S.key_shank_w - small.NAIL_D) / 2
    pieces = _axis_probe(piece, S.key_lip + 1.0)
    top = next(b.min.X for b in pieces if b.min.X > 20)
    assert top == pytest.approx(r_end + S.key_head_d / 2, abs=0.05)  # the head's room past the slot end
    from build123d import Pos
    cx, cy = small.center_xy(S)
    a = math.radians(small.key_angle(S))
    side = (S.key_shank_w + S.key_head_d) / 4  # beside the shank slot, under the head's room: where the lip is
    x = cx + r_end * math.cos(a) - side * math.sin(a)
    y = cy + r_end * math.sin(a) + side * math.cos(a)
    col = sorted((s.bounding_box() for s in (piece.children[0] & probe(x - 0.05, y - 0.05, 0, 0.1, 0.1, 60)).solids()),
                 key=lambda b: b.min.Z)
    assert col[-1].max.Z - col[-1].min.Z >= 2.0  # solid roof over the nail head
    assert col[0].max.Z == pytest.approx(S.key_lip)  # lip under it


def test_plate_is_one_object_four_filaments():
    plan = small.plan(S)
    assert len(plan) == 1 and plan[0].qty == 1 and [n for n, _ in plan[0].items] == ["sunflower_10in"]
    f = small.filament_for(S)
    assert (f("flower_yellow"), f("flower_orange"), f("flower_black"), f("flower_brown")) == (
        S.slot_petals, S.slot_beads, S.slot_center, S.slot_seeds)


@pytest.mark.slow
def test_slicer_slices_it_yellow_and_orange_then_black_then_brown(tmp_path):
    from cadkit import slicers
    from cadkit.settings import settings
    s = slicers.active()
    if not s.available() or settings().colors < 4:
        pytest.skip("needs a slicer that can run, and 4 colors")
    small.write(S, tmp_path)
    report = s.slice_report(tmp_path / "plates" / f"sunflower_10in{s.project_suffix}", tmp_path / "s.3mf")
    bands = [set(r[0]) for r in report["layers"]]
    i = bands.index({S.slot_center})
    assert {S.slot_petals, S.slot_beads} in bands[:i]
    assert all(b <= {S.slot_petals, S.slot_beads} for b in bands[:i])
    assert bands[i:] == [{S.slot_center}, {S.slot_seeds}]
