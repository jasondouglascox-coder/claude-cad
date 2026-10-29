"""Test first: the chimney prints upright with no supports and has the sizes asked for, derived from params."""
import json
import math
import zipfile

import pytest
from build123d import Align, Box, Pos

from cadkit import bambu, gcode, slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from lamp_chimney import build
from lamp_chimney.params import P
from lamp_chimney.parts import center, chimney

LAYER = P.printer.layer


@pytest.fixture(scope="module")
def part():
    return chimney(P)


def walls_at(part, z):
    """A thin probe across the centre along X at height z: the solid pieces' X extents, left to right."""
    cx, cy = center(P)
    probe = Pos(cx - P.foot_d, cy - 0.05, z - 0.05) * Box(2 * P.foot_d, 0.1, 0.1, align=(Align.MIN,) * 3)
    return sorted((b.min.X, b.max.X) for b in (s.bounding_box() for s in (part & probe).solids()))


def outer_r(part, z):
    (lo, _), (_, hi) = walls_at(part, z)
    return (hi - lo) / 2


def test_prints_flat_watertight_on_layers(part):
    assert printable_problems(part, P.printer) == []
    assert open_edges(part) == 0
    assert off_layer_z(part, P.printer) == []


def test_nothing_faces_down_above_the_bed(part):
    assert downward_faces(part) == []


def test_overall_height(part):
    bb = part.bounding_box()
    assert bb.max.Z - bb.min.Z == pytest.approx(P.height, abs=1e-3)


def test_foot_is_the_old_glass_outside_and_thick(part):
    (a0, a1), (b0, b1) = walls_at(part, P.foot_h / 2)
    assert b1 - a0 == pytest.approx(P.foot_d, abs=0.02)
    assert a1 - a0 == pytest.approx(P.foot_t, abs=0.02)
    assert b1 - b0 == pytest.approx(P.foot_t, abs=0.02)


@pytest.mark.parametrize("where,z,d", [("body", P.foot_h + P.foot_t + P.body_h / 2 - P.bend_r, P.foot_d),
                                       ("neck", (P.shoulder_top + P.height) / 2 + P.bend_r / 2, P.neck_d)])
def test_one_line_wall(part, where, z, d):
    (a0, a1), (b0, b1) = walls_at(part, z)
    assert b1 - a0 == pytest.approx(d, abs=0.02)
    assert a1 - a0 == pytest.approx(P.wall, abs=0.01)
    assert b1 - b0 == pytest.approx(P.wall, abs=0.01)


def test_open_at_both_ends(part):
    assert len(walls_at(part, LAYER / 2)) == 2
    assert len(walls_at(part, P.height - LAYER / 2)) == 2


def test_shoulder_is_rounded_and_never_steeper_than_asked(part):
    """Layer by layer through the shoulder the outside only comes in, never more than the angle allows per layer, and
    it eases in and out of the bends instead of turning at a corner."""
    z0, z1 = P.shoulder_z - P.bend_r, P.shoulder_top + P.bend_r
    zs = [z0 + LAYER * k for k in range(int((z1 - z0) / LAYER) + 1)]
    rs = [outer_r(part, z) for z in zs]
    steps = [a - b for a, b in zip(rs, rs[1:])]
    most = LAYER * math.tan(math.radians(P.shoulder_deg))
    assert all(-1e-3 < s <= most + 1e-3 for s in steps)
    assert max(steps) == pytest.approx(most, rel=0.05)  # the straight 45 in the middle
    moving = [s for s in steps if s > 1e-3]
    assert moving[0] < most / 3 and moving[-1] < most / 3  # rounded bends, not corners
    assert rs[0] == pytest.approx(P.foot_d / 2, abs=0.01) and rs[-1] == pytest.approx(P.neck_d / 2, abs=0.01)


def test_build_writes_a_white_plate_with_brims_and_thin_walls(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "render" / "iso.png").exists() and (tmp_path / "step" / "lamp_chimney.step").exists()
    s = slicers.active()
    project = tmp_path / "plates" / f"lamp_chimney_1{s.project_suffix}"
    got = {n: parts for n, _, parts in s.read_filaments(project)}
    assert set(got) == {"lamp_chimney"}
    conf = json.loads(zipfile.ZipFile(project).read("Metadata/project_settings.config"))
    assert conf["filament_colour"][P.filament_white - 1].upper() == "#FFFFFF"
    assert conf["brim_type"] == "outer_and_inner" and float(conf["brim_width"]) == P.brim
    assert conf["wall_generator"] == "arachne"


@pytest.mark.slow
@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_prints_one_line_with_brims_inside_and_out(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    report = s.slice_report(tmp_path / "plates" / f"lamp_chimney_1{s.project_suffix}", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(P.filament_white,)]
    moves = gcode.extrusions(bambu.plate_gcode(tmp_path / "s.3mf"))
    cx, cy, _ = gcode.centre_of_mass(bambu.plate_gcode(tmp_path / "s.3mf"))

    def r(m):
        return math.hypot((m[0] + m[2]) / 2 - cx, (m[1] + m[3]) / 2 - cy)

    neck_z = min({m[4] for m in moves}, key=lambda z: abs(z - (P.shoulder_top + P.height) / 2))
    neck = [m for m in moves if m[4] == neck_z]
    assert {m[5] for m in neck} == {"Outer wall"}  # one bead, no inner wall
    assert max(r(m) for m in neck) - min(r(m) for m in neck) < P.wall  # one loop round
    brim = [r(m) for m in moves if m[5] == "Brim"]
    assert min(brim) < P.foot_d / 2 - P.foot_t - P.brim / 2  # inside the foot
    assert max(brim) > P.foot_d / 2 + P.brim / 2  # and outside it
