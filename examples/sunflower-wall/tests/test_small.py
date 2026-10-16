"""The 10-inch flower printed in one go: every part stacked in place on one plate, three colors by height,
nothing over air, and a keyhole that hangs it centered in the user's wall gap."""
import math

import pytest
from build123d import Compound

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


def test_prints_flat_on_the_bed_in_three_colors_by_height(piece):
    yellow, black, brown = piece.children
    assert printable_problems(yellow, S.printer) == []
    assert [b.label for b in piece.children] == ["flower_yellow", "flower_black", "flower_brown"]
    for b in piece.children:
        assert off_layer_z(b, S.printer) == []
    assert black.bounding_box().min.Z == pytest.approx(yellow.bounding_box().max.Z)  # one change to black
    assert brown.bounding_box().min.Z == pytest.approx(black.bounding_box().max.Z)  # one change to brown
    assert unsupported(black, yellow) == pytest.approx(0, abs=1e-6)
    assert unsupported(Compound(children=brown.solids()[::40]), black) == pytest.approx(0, abs=1e-6)


def test_nothing_starts_over_air(piece):
    """Front petals are filled down to the bed; the only roof is the keyhole's small top strip."""
    for body in piece.children[:2]:
        assert all(a < 3.0 for _, a in downward_faces(body)), downward_faces(body)


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
    x, y = cx + r_end * math.cos(a), cy + r_end * math.sin(a)
    col = sorted((s.bounding_box() for s in (piece.children[0] & probe(x - 0.05, y - 0.05, 0, 0.1, 0.1, 60)).solids()),
                 key=lambda b: b.min.Z)
    assert col[-1].max.Z - col[-1].min.Z >= 2.0  # solid roof over the nail head
    assert col[0].max.Z == pytest.approx(S.key_lip)  # lip under it


def test_plate_is_one_object_three_filaments():
    plan = small.plan(S)
    assert len(plan) == 1 and plan[0].qty == 1 and [n for n, _ in plan[0].items] == ["sunflower_10in"]
    f = small.filament_for(S)
    assert (f("flower_yellow"), f("flower_black"), f("flower_brown")) == (S.slot_petals, S.slot_center, S.slot_seeds)


@pytest.mark.slow
def test_bambu_slices_it_yellow_then_black_then_brown(tmp_path):
    from cadkit import bambu
    if bambu.find() is None:
        pytest.skip("Bambu Studio not installed")
    small.write(S, tmp_path)
    report = bambu.slice_report(tmp_path / "plates" / "sunflower_10in.3mf", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(S.slot_petals,), (S.slot_center,), (S.slot_seeds,)]
