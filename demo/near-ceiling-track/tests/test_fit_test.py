import pytest

from hotrain.params import P
from hotrain.parts import fit_test


def test_fit_test_fits_bed_and_has_every_piece():
    ft = fit_test.make(P)
    bb = ft.bounding_box()
    assert bb.max.X <= P.bed_usable and bb.max.Y <= P.bed_usable
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    solids = ft.solids()
    assert all(s.is_valid for s in solids)
    assert len(solids) == 3 + 2 + 3 + 1 + 2 + 3  # grooves, slot plate + tab strip, key blocks, key, latch pair, rod snaps


def test_groove_variants_marked_distinctly():
    vols = [fit_test.groove_sample(P, 0.2, n).volume for n in (1, 2, 3)]
    assert vols[0] - vols[1] > 0.3 and vols[1] - vols[2] > 0.3
