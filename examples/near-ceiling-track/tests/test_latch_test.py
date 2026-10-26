"""Latch coupon: four pier-slot latches, identical but for the spring slot beside the finger (40 / 25 / 15 mm / none,
marked 1-4 notches), and two pier stubs. The first fit test's latch flexed so much the stub fell out."""
import pytest

from cadkit.checks import printable_problems
from hotrain.params import P
from hotrain.parts import fit_test


def test_variant_one_is_todays_latch_and_four_has_no_slot():
    assert fit_test.LATCH_SLOTS[0] == P.latch_finger_len
    assert fit_test.LATCH_SLOTS[-1] == 0.0
    assert list(fit_test.LATCH_SLOTS) == sorted(fit_test.LATCH_SLOTS, reverse=True)


def test_each_variant_cuts_its_slot_and_nothing_else():
    """Blocks differ only by the spring slot: latch_relief wide, the variant's length deep, bracket_t thick."""
    solid = fit_test.latch_variant(P, 0.0, 0).volume
    for slot in fit_test.LATCH_SLOTS:
        removed = solid - fit_test.latch_variant(P, slot, 0).volume
        assert removed == pytest.approx(P.latch_relief * slot * P.bracket_t, rel=0.03, abs=0.01)


def test_variants_marked_distinctly():
    vols = [fit_test.latch_variant(P, fit_test.LATCH_SLOTS[0], n).volume for n in (1, 2, 3, 4)]
    assert all(a - b > 0.3 for a, b in zip(vols, vols[1:]))


def test_coupon_prints_on_one_bed():
    c = fit_test.latch_coupon(P)
    assert len(c.solids()) == len(fit_test.LATCH_SLOTS) + 2  # four latches, two pier stubs
    bb = c.bounding_box()
    assert bb.max.X <= P.bed_usable and bb.max.Y <= P.bed_usable
    for s in c.solids():
        assert printable_problems(s, P.printer) == []


def test_build_writes_the_latch_plate(tmp_path):
    from cadkit import slicers
    from hotrain import build
    assert build.main(["latch-test", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "latch_test" / f"latch_test{slicers.active().project_suffix}").exists()
    assert "latch_test" in (tmp_path / "latch_test" / "plates.csv").read_text(encoding="utf-8")
