"""Test first: every rule a print has to meet, derived from params (no magic numbers)."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.settings import settings
from cadkit.checks import off_layer_z, open_edges, printable_problems, unsupported
from fitcoupon import build
from fitcoupon.parts import coupon, hole_x, peg
from fitcoupon.params import P


@pytest.fixture(scope="module")
def parts():
    return coupon(P), peg(P)


def test_each_part_prints_flat_watertight_on_layers(parts):
    c, pin = parts
    assert printable_problems(c.children[0]) == [] and printable_problems(pin) == []
    for body in (*c.children, pin):
        assert open_edges(body) == 0
        assert off_layer_z(body, P.printer) == []


def test_marks_rest_on_the_plate(parts):
    """Two colors, one change: the marks start on the plate's top layer, never over a hole or air."""
    base, marks = parts[0].children
    assert unsupported(marks, base) == pytest.approx(0, abs=1e-9)
    assert marks.bounding_box().min.Z == pytest.approx(base.bounding_box().max.Z)


@pytest.mark.parametrize("k", range(len(P.clearances)))
def test_hole_is_peg_plus_clearance(parts, k):
    """Probe across the hole: the gap in a thin slab is the hole diameter."""
    base = parts[0].children[0]
    y = P.plate_w / 2 + 2
    probe = Pos(hole_x(P, k) - P.pitch / 2, y - 0.05, P.plate_t / 2) * Box(P.pitch, 0.1, 0.1, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (base & probe).solids()), key=lambda b: b.min.X)
    assert pieces[1].min.X - pieces[0].max.X == pytest.approx(P.peg_d + P.clearances[k], abs=0.02)


def test_build_writes_a_colored_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "render" / "iso.png").exists()
    s = slicers.active()
    got = dict((n, parts) for n, _, parts in s.read_filaments(tmp_path / "plates" / f"fit_coupon_1{s.project_suffix}"))
    f = settings().filament
    assert got["coupon"] == {"coupon_base": f(1), "coupon_marks": f(2)}


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_with_one_color_change(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"fit_coupon_1{s.project_suffix}", tmp_path / "s.3mf")
    bands = [(1,), (2,)] if settings().colors > 1 else [(1,)]
    assert [r[0] for r in report["layers"]] == bands
