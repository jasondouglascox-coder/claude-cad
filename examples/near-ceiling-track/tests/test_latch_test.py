"""The pier latch, from two coupon prints: the spring slot let the finger flex so the pier fell out, and the no-slot
latch was best but still a little loose. Now: no slot, a tighter pier slot, a longer hook. The latch coupon tries the
hook at three lengths (1-3 notches), all without the slot, with two pier stubs."""
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import printable_problems
from hotrain.params import P
from hotrain.parts import bracket, fit_test


def test_brackets_latch_rigid_with_the_tighter_slot_and_longer_hook():
    assert P.latch_finger_len == 0.0  # no spring slot
    assert bracket.slot_w(P) == pytest.approx(P.panel_t + P.fit_pier)
    assert P.fit_pier < P.fit_slide
    assert P.latch_engage in fit_test.LATCH_ENGAGES


def _hook_reach(block):
    """How far the hook stands into the pier slot: the slot's narrowest gap vs its width, probed at every height."""
    bb = block.bounding_box()
    widths = []
    z = 1.5  # above the identifying notches on the bottom edge
    while z < bb.size.Y - 0.2:
        probe = Pos(bb.min.X - 1, z, bb.size.Z / 2) * Box(bb.size.X + 2, 0.05, 0.05, align=(Align.MIN,) * 3)
        pieces = sorted((s.bounding_box() for s in (block & probe).solids()), key=lambda b: b.min.X)
        gaps = [b.min.X - a.max.X for a, b in zip(pieces, pieces[1:]) if 0.5 < b.min.X - a.max.X < 5]
        widths += gaps
        z += 0.1
    return max(widths) - min(widths), max(widths)


@pytest.mark.parametrize("k", range(3))
def test_coupon_hook_lengths(k):
    e = fit_test.LATCH_ENGAGES[k]
    block = fit_test.latch_variant(P, e, k + 1)
    assert printable_problems(block, P.printer) == []
    reach, slot = _hook_reach(block)
    assert slot == pytest.approx(P.panel_t + P.fit_pier, abs=0.02)
    assert reach == pytest.approx(e, abs=0.06)


def test_coupon_has_no_spring_slots():
    solid = fit_test.latch_variant(P, P.latch_engage, 0)
    assert len(solid.solids()) == 1
    bb = solid.bounding_box()
    # the block is solid beside the slot: no cut runs down past the hook from the top
    side = Pos(bb.max.X - 4.5, bb.max.Y - 30, 0) * Box(1.5, 25, P.bracket_t, align=(Align.MIN,) * 3)
    assert (solid & side).volume == pytest.approx(side.volume, rel=1e-3)


def test_coupon_prints_on_one_bed():
    c = fit_test.latch_coupon(P)
    assert len(c.solids()) == len(fit_test.LATCH_ENGAGES) + 2  # the latches, two pier stubs
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
