"""The cross-frame clip coupon: a short top of the cross-frame at CF_FITS slot clearances (1-3 notches), to push
onto an already printed bay's panels at a post and pick the one that stays put."""
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import printable_problems
from hotrain.params import P
from hotrain.parts import cross_frame, fit_test


def _gaps(clip, y):
    """Open gaps across the clip at height y (the slots), left to right."""
    bb = clip.bounding_box()
    probe = Pos(bb.min.X - 1, y, bb.size.Z / 2) * Box(bb.size.X + 2, 0.05, 0.05, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (clip & probe).solids()), key=lambda b: b.min.X)
    return [b.min.X - a.max.X for a, b in zip(pieces, pieces[1:])]


@pytest.mark.parametrize("k", range(3))
def test_clip_slots(k):
    f = fit_test.CF_FITS[k]
    clip = fit_test.cf_clip(P, f, k + 1)
    assert printable_problems(clip, P.printer) == []
    assert len(clip.solids()) == 1
    bb = clip.bounding_box()
    assert bb.size.X == pytest.approx(P.rail_ctc + P.panel_t + f + 2 * P.cf_wall, abs=0.01)  # the real walls
    gaps = _gaps(clip, bb.size.Y - 1.0)
    assert gaps == pytest.approx([P.panel_t + f] * 2, abs=0.01)
    assert fit_test.CF_CLIP_SLOT < bb.size.Y  # the slots are open at the top, closed below


def test_clip_slots_sit_on_the_rails_spacing():
    clip = fit_test.cf_clip(P, P.fit_cf, 2)
    bb = clip.bounding_box()
    probe_y = bb.size.Y - 1.0
    pieces = sorted((s.bounding_box() for s in (clip & (Pos(-1, probe_y, bb.size.Z / 2) * Box(
        bb.size.X + 2, 0.05, 0.05, align=(Align.MIN,) * 3))).solids()), key=lambda b: b.min.X)
    centers = [(a.max.X + b.min.X) / 2 for a, b in zip(pieces, pieces[1:])]
    assert centers[1] - centers[0] == pytest.approx(P.rail_ctc, abs=0.01)


def test_clip_coupon_on_one_plate(tmp_path):
    from cadkit import slicers
    from hotrain import build
    c = fit_test.cf_clip_coupon(P)
    assert len(c.solids()) == len(fit_test.CF_FITS)
    assert build.main(["cf-clip-test", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "cf_clip_test" / f"cf_clip_test{slicers.active().project_suffix}").exists()
