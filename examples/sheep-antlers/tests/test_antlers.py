"""Test first: the antlers print flat, one solid, with a nub sized for the slot, from params.

Print orientation: the plate lies on its back on the bed; the sheep's up is +Y, across is X, the nub points up (+Z)
toward the sheep's nose."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.settings import settings
from sheep_antlers import build
from sheep_antlers.params import P, Params
from sheep_antlers.parts import antlers, center_x


@pytest.fixture(scope="module")
def part():
    return antlers(P)


def slab(part, z0, z1):
    probe = Pos(-500, -500, z0) * Box(1000, 1000, z1 - z0, align=(Align.MIN,) * 3)
    return part & probe


def test_prints_flat_one_solid_watertight_on_layers(part):
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []
    assert downward_faces(part) == []


def test_plate_thickness_and_size(part):
    plate = slab(part, 0.1, P.t - 0.1).bounding_box()
    assert plate.size.X == pytest.approx(P.span, abs=0.05)
    assert plate.min.Y == pytest.approx(0, abs=1e-3)  # on the bed's edge; the slot bottom is at -P.bottom
    assert plate.max.Y == pytest.approx(P.height - P.bottom, abs=0.05)
    assert (plate.min.X + plate.max.X) / 2 == pytest.approx(center_x(P), abs=0.05)


def test_nub_fits_the_slot(part):
    nub = slab(part, P.t + 0.1, P.t + P.nub_depth - P.nub_chamfer - 0.1)
    assert len(nub.solids()) == 1
    bb = nub.bounding_box()
    assert bb.size.X == pytest.approx(P.nub_w, abs=0.02)
    assert bb.size.Y == pytest.approx(P.nub_h, abs=0.02)
    assert (bb.min.Y + bb.max.Y) / 2 == pytest.approx(P.slot_h / 2 - P.bottom, abs=0.02)  # centered on the slot
    assert bb.min.Y == pytest.approx(0, abs=0.02)  # nothing hangs below the nub onto the sheep
    assert (bb.min.X + bb.max.X) / 2 == pytest.approx(center_x(P), abs=0.02)
    assert part.bounding_box().max.Z == pytest.approx(P.t + P.nub_depth, abs=1e-3)


def test_nub_tip_has_a_lead_in(part):
    tip = slab(part, P.t + P.nub_depth - 0.1, P.t + P.nub_depth).bounding_box()
    assert tip.size.Y < P.nub_h - P.nub_chamfer


def test_band_is_only_band_h_tall(part):
    """On the center line the plate runs solid from the slot bottom to band_h (level with the head top: no thick
    brown showing above it), then nothing until the antlers."""
    probe = Pos(center_x(P) - 0.05, -1, 0.1) * Box(0.1, 200, P.t - 0.2, align=(Align.MIN,) * 3)
    spans = sorted((b.min.Y, b.max.Y) for b in (s.bounding_box() for s in (part & probe).solids()))
    assert spans[0][0] == pytest.approx(0, abs=1e-3)
    assert spans[0][1] == pytest.approx(P.band_h - P.bottom, abs=0.05)
    assert len(spans) == 1


def test_tips_are_not_too_thin(part):
    """Cut across near the top: each tine there is at least tip_w wide."""
    y = P.height - P.bottom - P.tip_w / 2
    probe = Pos(-500, y - 0.05, 0.1) * Box(1000, 0.1, P.t - 0.2, align=(Align.MIN,) * 3)
    widths = [s.bounding_box().size.X for s in (part & probe).solids()]
    assert len(widths) == 2 and all(w > P.tip_w * 0.6 for w in widths)  # round tips: narrower at the very top


def test_mirror_symmetric(part):
    bb = part.bounding_box()
    c = center_x(P)
    left = slab(part, 0.1, P.t - 0.1) & (Pos(-500, -500, 0) * Box(500 + c, 1000, 100, align=(Align.MIN,) * 3))
    right = slab(part, 0.1, P.t - 0.1) & (Pos(c, -500, 0) * Box(500, 1000, 100, align=(Align.MIN,) * 3))
    assert left.volume == pytest.approx(right.volume, rel=1e-3)
    assert bb.size.X == pytest.approx(P.span, abs=0.05)


def test_thin_tips_refused():
    with pytest.raises(ValueError, match="tip_w"):
        Params(tip_w=1.6)


def test_build_writes_a_brown_petg_plate(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "step" / "sheep_antlers.step").exists()
    assert (tmp_path / "render" / "front.png").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"sheep_antlers_1{s.project_suffix}")}
    assert got == {"sheep_antlers": settings().filament(P.filament_brown)}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_one_filament(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"sheep_antlers_1{s.project_suffix}"
    back = s.roundtrip(plate)
    assert s.same_objects(back, plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_brown),)]


def test_band_stays_under_the_head_arc(part):
    """Off center the band's top follows the head's top arc (head_r), so no brown shows above the head at the
    sides. Probe straight up near each end of the band: its lowest piece (the band) tops out under the arc."""
    import math
    # outside the beams (root_x + beam_w / 2, plus the round where they join): there the antler itself rises
    for dx in (P.band_half - 0.5, -(P.band_half - 0.5)):
        assert abs(dx) > P.root_x + P.beam_w / 2 + P.smooth
        x = center_x(P) + dx
        probe = Pos(x - 0.05, 0, 0.1) * Box(0.1, P.head_top - P.bottom, P.t - 0.2, align=(Align.MIN,) * 3)
        pieces = sorted((b.min.Y, b.max.Y) for b in (s.bounding_box() for s in (part & probe).solids()))
        if not pieces:
            continue  # the band's rounded end stops short of here
        arc_y = P.head_top - P.head_r + math.sqrt(P.head_r ** 2 - dx ** 2) - P.bottom
        assert pieces[0][1] <= arc_y + 0.05, (dx, pieces[0][1], arc_y)


def test_head_arc_curves_enough_at_the_band_ends():
    """The first print showed 1 mm+ of brown at the sides with head_r 30: the arc must drop more than that did."""
    import math
    drop = lambda r: r - math.sqrt(r * r - 16.0 ** 2)
    assert drop(P.head_r) >= drop(30.0) + 2.0
