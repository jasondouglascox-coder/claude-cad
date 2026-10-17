"""Stainless wire rail on a printed web: the 2D profile, the gauge wheels feel, and the 18° curve test piece.
docs/specs/2026-10-16-wire-rail-design.md"""
import math
from dataclasses import replace
from functools import lru_cache

import pytest
from build123d import Align, Box, Pos, Rot

from cadkit.checks import off_layer_z, open_edges, printable_problems, unsupported
from cadkit.clash import find_clashes
from hotrain import wire_rail as W
from hotrain.params import INCH, P
from hotrain.parts import wire_curve


@lru_cache(maxsize=None)
def bodies():
    return wire_curve.bodies(P)


# --- profile -------------------------------------------------------------------------------------------------
def test_profile_clears_the_flange_and_tread_keep_outs():
    assert W.check_envelopes(W.profile_pts(P), P) == {"flange": 0.0, "tread": 0.0}


def test_envelope_check_catches_a_raised_lip():
    raised = [(x, z + 0.5) for x, z in W.profile_pts(P)]
    hits = W.check_envelopes(raised, P)
    assert hits["tread"] > 0.01


def test_every_gray_feature_is_wide_enough_to_print():
    """Classic walls drop anything under two lines wide (the first slice lost the lip; a gauge-side wedge never
    printed): no step of the profile is narrower, measured across each horizontal top."""
    pts = W.profile_pts(P)
    nozzle = W.fine_printer(P).nozzle
    for (x0, z0), (x1, z1) in zip(pts, pts[1:] + pts[:1]):
        if abs(z0 - z1) < 1e-9 and abs(x1 - x0) > 1e-3:
            assert abs(x1 - x0) >= 1.4 * nozzle, f"top at z {z0:.2f} only {abs(x1 - x0):.2f} mm wide"


def test_no_sliver_beside_the_wire_on_the_gauge_side():
    """The 1.6 mm deep-flange keep-out leaves no room for a printable wall beside the 1.29 mm wire on the gauge side:
    nothing there rises above the wire's bottom (a wedge there never printed with classic walls, and Arachne printed
    it as a fat bead into the seat and the keep-out)."""
    assert max(z for x, z in W.profile_pts(P) if x < -1e-6) <= -P.wire_d + 1e-6


def test_profile_tops_on_fine_layers_and_seat_under_the_wire():
    pts = W.profile_pts(P)
    fp = W.fine_printer(P)
    zs = {round(z, 6) for (x0, z), (x1, z1) in zip(pts, pts[1:] + pts[:1]) if abs(z - z1) < 1e-9 and abs(x1 - x0) > 1e-3}
    assert all(fp.on_layer(P.rail_top + z) for z in zs), sorted(zs)
    assert min(z for _, z in pts) == pytest.approx(P.tie_h - P.rail_top)
    # the cradle's lowest point under the wire is the wire bottom: wire top lands on rail_top
    under = [z for x, z in pts if abs(x) < 0.02]
    assert max(under) == pytest.approx(-P.wire_d, abs=1e-3)


def test_field_lip_is_two_nozzle_lines_wide_all_the_way_down():
    """Bambu (classic walls) drops a wall one line wide: the first slice left the whole lip off. Two lines at the
    top, and the field face is vertical so it only widens below."""
    pts = W.profile_pts(P)
    nozzle = W.fine_printer(P).nozzle
    top = max(z for x, z in pts if x > 0)
    xs = [x for x, z in pts if abs(z - top) < 1e-9]
    assert max(xs) - min(xs) >= 2 * nozzle
    outer = max(x for x, _ in pts)
    assert [z for x, z in pts if abs(x - outer) < 1e-9] == pytest.approx([P.tie_h - P.rail_top, top])


# --- gauge the wheels feel -----------------------------------------------------------------------------------
def test_rp25_wheels_feel_a_gauge_inside_s32():
    g = W.effective_gauge(P, P.wheel_d_rp25)
    assert 0.649 * INCH <= g <= 0.661 * INCH, g / INCH


def test_deep_vintage_flanges_keep_play_both_ways():
    assert W.max_shift(P, P.flange_depth_max) > 0.05


def test_deep_flange_contacts_lower_and_steeper_than_rp25():
    """The deeper the flange, the closer to vertical it meets the round wire (flange-climb resistance)."""
    assert W.contact_angle(P, P.flange_depth_max) > W.contact_angle(P, P.wheel_d_rp25) > 65.0


# --- the curve test piece -----------------------------------------------------------------------------------
def test_piece_prints_on_fine_layers():
    fp = W.fine_printer(P)
    part = wire_curve.make(P)
    assert printable_problems(part, fp) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, fp) == []


def test_one_seam_gray_never_over_air():
    b = bodies()
    assert b["wood"].bounding_box().max.Z == pytest.approx(P.tie_h)
    assert b["steel"].bounding_box().min.Z == pytest.approx(P.tie_h)
    assert b["steel"].bounding_box().max.Z < P.rail_top
    assert unsupported(b["steel"], b["wood"]) == pytest.approx(0, abs=1e-3)
    assert len(b["wood"].solids()) == 1


def test_wire_seats_on_the_curve_radius():
    """Probe the webs across the middle tie gap: the cradle low points sit curve_r +/- (gauge + wire_d)/2 out."""
    steel = bodies()["steel"]
    y_in, y_out = P.curve_r - W.y_wire(P), P.curve_r + W.y_wire(P)
    for y in (y_in, y_out):
        z_floor = P.rail_top - P.wire_d
        below = Pos(0, y, z_floor - 0.05) * Box(0.3, 0.3, 0.1)
        above = Pos(0, y, z_floor + 0.15) * Box(0.3, 0.3, 0.1)
        assert (steel & below).volume > 0.005, "no seat floor under the wire"
        assert (steel & above).volume == pytest.approx(0, abs=1e-6), "plastic where the wire goes"


def test_pieces_chain_into_the_corner():
    assert P.wire_test_pieces * P.wire_test_deg == pytest.approx(90.0)
    a = wire_curve.make_assembly_piece(P)
    b = Rot(0, 0, -P.wire_test_deg) * a  # the next piece, clockwise along the track
    assert find_clashes([("a", a), ("b", b)]) == []
    # the tab really sits in the socket: grown a little, it would hit
    tight = wire_curve.make_assembly_piece(replace(P, fit_snap=-0.1))
    assert find_clashes([("a", tight), ("b", Rot(0, 0, -P.wire_test_deg) * tight)])


@pytest.mark.parametrize("depth", ["rp25", "deep"])
@pytest.mark.parametrize("side", [1, -1])
def test_wheelset_flanging_on_the_curve_touches_no_plastic(depth, side):
    D = P.wheel_d_rp25 if depth == "rp25" else P.flange_depth_max
    wheels = wire_curve.wheelset(P, D, side * (W.max_shift(P, D) - 0.01))
    piece = wire_curve.make_assembly_piece(P)
    for w in wheels:
        assert (w & piece).volume == pytest.approx(0, abs=1e-4)
        assert w.distance_to(piece) > 0.0
    # the check can fail: a flange 0.3 mm deeper than the keep-out hits the web
    if depth == "deep" and side == 1:
        sunk = wire_curve.wheelset(P, P.flange_depth_max + 0.3, W.max_shift(P, P.flange_depth_max + 0.3) - 0.01)
        assert sum((w & piece).volume for w in sunk) > 1e-4


def test_piece_fits_the_bed_and_the_corner_fits_two_plates():
    from hotrain import plates
    pls = plates.wire_test_plates(P)
    assert [pl.name for pl in pls][:1] == ["wire_curve_single"]
    corner = [pl for pl in pls if pl.name.startswith("wire_curve_corner")]
    assert 1 <= len(corner) <= 2
    assert sum(len(pl.items) for pl in corner) == P.wire_test_pieces
    for pl in pls:
        for _, s in pl.items:
            bb = s.bounding_box()
            assert bb.max.X <= P.bed_usable + 1e-6 and bb.max.Y <= P.bed_usable + 1e-6


# --- build: plates at fine layers --------------------------------------------------------------------------
def _project_layers(path):
    import json
    import zipfile
    cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    return float(cfg["layer_height"]), float(cfg["initial_layer_print_height"])


@pytest.fixture(scope="module")
def wire_test_out(tmp_path_factory):
    from hotrain import build
    out = tmp_path_factory.mktemp("wt")
    assert build.main(["wire-test", "--out", str(out)]) == 0
    return out / "wire_test"


def test_wire_test_writes_plates_and_sheet(wire_test_out):
    import csv
    with open(wire_test_out / "plates.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["plate"] == "wire_curve_single" and rows[0]["contents"] == "wire_curve x1"
    assert sum(int(r["contents"].split("x")[-1]) for r in rows[1:]) == P.wire_test_pieces
    assert (wire_test_out / "wire_curve_single.step").stat().st_size > 1000
    assert (wire_test_out / "render" / "wire_curve_test.png").stat().st_size > 1000


def test_wire_test_plates_open_brown_gray_at_fine_layers(wire_test_out):
    from cadkit import slicers
    from cadkit.settings import settings
    s = slicers.active()
    path = wire_test_out / f"wire_curve_single{s.project_suffix}"
    f = settings().filament
    assert s.read_filaments(path) == [("wire_curve", f(P.filament_brown),
                                       {"wire_curve_wood": f(P.filament_brown), "wire_curve_steel": f(P.filament_gray)})]
    if s.name == "bambu":
        import json
        import zipfile
        assert _project_layers(path) == (P.wire_layer, P.wire_first_layer)
        cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
        assert cfg["wall_generator"] == "classic"  # Arachne prints thin features as fat beads: into the wire seat


@pytest.mark.slow
@pytest.mark.parametrize("plate", ["wire_curve_single", "wire_curve_corner"])
def test_wire_test_slices_with_one_swap_at_the_tie_tops(wire_test_out, plate):
    """Bambu slices each plate at the fine layers: brown up to tie_h, then gray to the lip top, one swap."""
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    rep = s.slice_report(wire_test_out / f"{plate}{s.project_suffix}")
    seam = round((P.tie_h - P.wire_first_layer) / P.wire_layer)  # layer index of the last brown layer
    lip_top = P.rail_top + max(z for x, z in W.profile_pts(P) if x > 0)
    last = round((lip_top - P.wire_first_layer) / P.wire_layer)  # layer index of the lip's top layer
    assert rep["layers"] == [((P.filament_brown,), 0, seam), ((P.filament_gray,), seam + 1, last)], \
        "every layer up to the lip top prints, brown then gray"


@pytest.mark.slow
def test_corner_plate_survives_the_slicer(wire_test_out, tmp_path):
    """The 5-piece plate comes back from the slicer as 5 objects, same geometry, each brown and gray."""
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    path = next(wire_test_out.glob(f"wire_curve_corner*{s.project_suffix}"))
    back = s.roundtrip(path, tmp_path / f"rt{s.project_suffix}")
    assert s.same_objects(back, path)
    fils = s.read_filaments(back)
    assert sorted(fils) == sorted(s.read_filaments(path)) and len(fils) == P.wire_test_pieces
