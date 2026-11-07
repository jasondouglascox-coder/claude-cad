"""Fit coupon: a rail fork and a gap gauge. Expectations from params."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import off_layer_z, open_edges, printable_problems
from speaker_shelf import build
from speaker_shelf.parts import fork_slot_x, gap_center_x, gap_gauge, rail_fork
from speaker_shelf.params import P


@pytest.fixture(scope="module")
def fork():
    return rail_fork(P)


@pytest.fixture(scope="module")
def gauge():
    return gap_gauge(P)


def _pieces_x(part, x0, x1, y, z):
    probe = Pos(x0, y - 0.05, z) * Box(x1 - x0, 0.1, 0.1, align=(Align.MIN,) * 3)
    return sorted((s.bounding_box() for s in (part & probe).solids()), key=lambda b: b.min.X)


@pytest.mark.parametrize("name", ["fork", "gauge"])
def test_prints_flat_watertight_on_layers(name, request):
    part = request.getfixturevalue(name)
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []


@pytest.mark.parametrize("k", range(len(P.fork_slots)))
def test_fork_slot_widths(fork, k):
    x = fork_slot_x(P, k)
    w = P.fork_slots[k]
    pieces = _pieces_x(fork, x - w / 2 - 1, x + w / 2 + 1, P.fork_spine + P.fork_depth / 2, P.fork_h / 2)
    assert pieces[1].min.X - pieces[0].max.X == pytest.approx(w, abs=0.01)


def test_fork_slots_reach_past_the_rail(fork):
    assert P.fork_depth > max(P.fork_slots)


def test_fork_labels_are_engraved(fork):
    """The label strip has a cut in its top: a probe there finds less than full height."""
    x = fork_slot_x(P, 0)
    assert fork.bounding_box().max.Z == pytest.approx(P.fork_h)
    assert fork.volume < (P.fork_l * (P.fork_spine + P.fork_depth) - sum(P.fork_slots) * P.fork_depth) * P.fork_h - 1


@pytest.mark.parametrize("k", range(len(P.gap_steps)))
def test_gap_step_lengths(gauge, k):
    L = P.gap_steps[k]
    y = (k + 0.5) * P.gap_step_d
    cx = gap_center_x(P)
    pieces = _pieces_x(gauge, cx - L / 2 - 2, cx + L / 2 + 2, y, P.gap_h / 2 - P.label_depth)
    assert len(pieces) == 1
    assert pieces[0].max.X - pieces[0].min.X == pytest.approx(L, abs=0.01)


def test_build_writes_one_black_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "render" / "fit_coupon.png").exists()
    s = slicers.active()
    got = dict((n, parts) for n, _, parts in s.read_filaments(tmp_path / "plates" / f"fit_coupon{s.project_suffix}"))
    assert set(got) == {"rail_fork", "gap_gauge"}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_one_color(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"fit_coupon{s.project_suffix}", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(P.filament_black,)]


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_the_shelf_in_one_color(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"speaker_shelf{s.project_suffix}", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(P.filament_black,)]
    got = dict((n, parts) for n, _, parts in s.read_filaments(tmp_path / "plates" / f"speaker_shelf{s.project_suffix}"))
    assert set(got) == {"speaker_shelf"}
