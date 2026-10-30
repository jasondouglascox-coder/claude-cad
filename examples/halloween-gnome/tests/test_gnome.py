"""Test first: every rule the three prints have to meet, derived from params (no magic numbers)."""
import math

import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import off_layer_z, open_edges, overhangs, printable_problems, unsupported
from cadkit.mesh import Mesh
from halloween_gnome import gnome
from halloween_gnome.params import P

MIN = (Align.MIN, Align.MIN, Align.MIN)


def on_bed(meshes: list[Mesh]) -> list[Mesh]:
    """Moved together so the print sits at the bed's corner (the checks want positive x and y)."""
    lo = np.min([m.verts.min(0) for m in meshes], axis=0)
    return [m.translate((5 - lo[0], 5 - lo[1], 0)) for m in meshes]


PRINTS = {"body": lambda: gnome.body(P), "hat": lambda: gnome.hat(P), "nose": lambda: [gnome.nose(P)]}


@pytest.mark.parametrize("name", PRINTS)
def test_each_print_is_one_solid_flat_watertight_on_layers(name):
    bodies = on_bed(PRINTS[name]())
    whole = Mesh.union(bodies)
    assert printable_problems(whole, P.printer) == []
    for b in bodies:
        assert open_edges(b) == 0, b.label
        assert off_layer_z(b, P.printer) == [], b.label


@pytest.mark.parametrize("name", PRINTS)
def test_nothing_overhangs(name):
    """No supports: nothing faces down steeper than 45 degrees above the bed."""
    assert overhangs(Mesh.union(PRINTS[name]())) == []


@pytest.mark.parametrize("name", ["body", "hat"])
def test_each_colour_starts_on_the_one_below(name):
    bodies = PRINTS[name]()
    for lower, upper in zip(bodies, bodies[1:]):
        assert unsupported(upper, lower, probe=0.01) == pytest.approx(0, abs=0.05), upper.label  # thin: flares lean
        assert upper.bounding_box().min.Z == pytest.approx(lower.bounding_box().max.Z, abs=1e-6)


def test_colour_seams_where_params_put_them():
    black, orange, white = gnome.body(P)
    assert black.bounding_box().max.Z == pytest.approx(P.boot_h)
    assert orange.bounding_box().max.Z == pytest.approx(P.robe_h)
    brim, band, _ = gnome.hat(P)
    assert brim.bounding_box().max.Z == pytest.approx(P.brim_t)
    assert band.bounding_box().max.Z == pytest.approx(P.brim_t + P.band_h)


def test_two_inches_tall_assembled():
    top = max(m.bounding_box().max.Z for m in gnome.assembled(P))
    assert top == pytest.approx(P.height, abs=1e-3)
    assert P.height == pytest.approx(50.8)


def slab(z: float) -> Box:
    """A thin bar along x through the axis at height z."""
    return Pos(-40, -0.05, z) * Box(80, 0.1, 0.1, align=MIN)


def test_tree_hole_is_half_an_inch_and_goes_up_to_its_roof():
    whole = Mesh.union(gnome.body(P))
    for z in (0.5, P.hole_depth / 2, P.hole_depth - 0.5):
        pieces = sorted((whole & slab(z)).solids(), key=lambda s: s.bounding_box().min.X)
        assert len(pieces) == 2
        gap = pieces[1].bounding_box().min.X - pieces[0].bounding_box().max.X
        assert gap == pytest.approx(P.hole_d, abs=0.02)
    up = Pos(-0.05, -0.05, 0) * Box(0.1, 0.1, P.shoulder_h, align=MIN)
    roof = (whole & up).bounding_box().min.Z  # the first material straight up the axis
    point = P.hole_depth + P.hole_d / 2 / math.tan(math.radians(P.hole_roof))
    assert P.hole_depth < roof <= point + 1e-6


def test_hat_wall_round_the_socket():
    """The crown leans back; the socket stays inside it with p.hat_wall all round."""
    for z in np.arange(P.brim_t + P.band_h, gnome.socket_apex(P), 0.2):
        c, r = gnome.crown(P, z)
        assert r - abs(c) - gnome.socket_r(P, z) >= P.hat_wall, z


def test_crown_leans_no_steeper_than_45():
    zs = np.arange(P.brim_t + P.band_h, P.hat_h, 0.2)
    outer = [sum(gnome.crown(P, z)) for z in zs]
    assert max(np.diff(outer) / 0.2) <= 1.0


def test_parts_fit_together_without_clashing():
    """Each part backed off its seat by a hair (flush faces leave the boolean degenerate slivers): no overlap.
    The seating test shows they touch."""
    black, orange, white = gnome.body(P)
    hair = 0.005
    for other in [h.translate((0, 0, hair)) for h in gnome.placed_hat(P)] + [gnome.placed_nose(P).translate((0, -hair, 0))]:
        for b in (black, orange, white):
            assert (b & other).volume == pytest.approx(0, abs=0.05), (b.label, other.label)


def test_hat_seats_on_the_shoulder_and_the_nose_on_the_face():
    white = gnome.body(P)[2]
    brim = gnome.placed_hat(P)[0]
    assert brim.bounding_box().min.Z == pytest.approx(P.shoulder_h)
    assert brim.gap(white) == pytest.approx(0, abs=0.01)
    assert gnome.placed_nose(P).gap(white) == pytest.approx(0, abs=0.01)


def test_nose_hole_is_the_peg_with_no_clearance():
    """Press fit: the hole's section is the peg's (p.nose_fit = 0), a little deeper than the peg is long."""
    nose = gnome.nose(P)
    probe = Pos(-10, -10, 1.0) * Box(20, 20, 0.1, align=MIN)
    ring = (nose & probe).volume / 0.1
    shape = gnome.teardrop(P.peg_r + P.nose_fit / 2, P.peg_angle)
    hole_area = 0.5 * abs(np.dot(shape[:, 0], np.roll(shape[:, 1], 1)) - np.dot(shape[:, 1], np.roll(shape[:, 0], 1)))
    ball = math.pi * (P.nose_r ** 2 - (1.05 - P.nose_back) ** 2)
    assert ball - ring == pytest.approx(hole_area, rel=0.02)
    assert P.nose_fit == 0
    peg = gnome.placed_nose(P) & gnome.peg(P)
    assert peg.volume == pytest.approx(0, abs=0.05)
    depth = P.peg_len + P.peg_room  # full section up to here, then the roof closes in
    holes = [ball_area(z) - (nose & (Pos(-10, -10, z) * Box(20, 20, 0.01, align=MIN))).volume / 0.01
             for z in (depth - 0.05, depth + 0.05)]
    assert holes[0] == pytest.approx(hole_area, rel=0.02)
    assert holes[1] < hole_area * 0.99


def ball_area(z: float) -> float:
    return math.pi * (P.nose_r ** 2 - (z - P.nose_back) ** 2)


def test_build_writes_a_plate_per_print_in_its_colours(tmp_path):
    from cadkit import slicers
    from cadkit.settings import settings
    from halloween_gnome import build
    assert build.main(["plates", "--out", str(tmp_path)]) == 0
    s, f = slicers.active(), settings().filament
    want = {"body": {"body_black": f(P.slot_black), "body_orange": f(P.slot_orange), "body_white": f(P.slot_white)},
            "hat": {"hat_brim": f(P.slot_black), "hat_band": f(P.slot_orange), "hat_crown": f(P.slot_black)},
            "nose": {"nose": f(P.slot_pink)}}
    for name, parts in want.items():
        got = {n: p for n, _, p in s.read_filaments(tmp_path / "plates" / f"gnome_{name}{s.project_suffix}")}
        assert got[f"gnome_{name}"] == parts


@pytest.mark.slow
@pytest.mark.parametrize("name, bands", [("body", [P.slot_black, P.slot_orange, P.slot_white]),
                                         ("hat", [P.slot_black, P.slot_orange, P.slot_black]),
                                         ("nose", [P.slot_pink])])
def test_slicer_prints_each_colour_band_once(tmp_path, name, bands):
    from cadkit import slicers
    from halloween_gnome import build
    s = slicers.active()
    if not s.available():
        pytest.skip("no slicer installed (settings: slicer)")
    build.main(["plates", "--out", str(tmp_path)])
    report = s.slice_report(tmp_path / "plates" / f"gnome_{name}{s.project_suffix}", tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(b,) for b in bands]
    top = {"body": P.shoulder_h + P.head_h, "hat": P.hat_h, "nose": P.nose_back + P.nose_r}[name]
    assert report["layers"][-1][2] + 1 == pytest.approx(top / P.printer.layer, abs=1)


def test_hat_grips_on_a_straight_collar():
    """A 35-degree cone can't hold by friction (tan 35 > PLA's ~0.3): the head and socket share a straight collar
    p.head_collar tall at head_r, a press fit, and taper above it."""
    head = gnome.head(P)
    for z in (0.6, P.head_collar - 0.1):
        probe = Pos(-20, -20, P.shoulder_h + z) * Box(40, 40, 0.01, align=MIN)
        assert (head & probe).volume / 0.01 == pytest.approx(math.pi * P.head_r ** 2, rel=0.002)
        assert gnome.socket_r(P, z) == pytest.approx(P.head_r)
    assert gnome.socket_r(P, P.head_collar + 1) < P.head_r
    assert P.head_collar >= 2.0


def test_hole_mouths_are_chamfered():
    """The first layer squishes out: every hole's mouth flares by p.mouth_run, closing to size p.mouth_rise up."""
    z = 0.05
    flare = 2 * P.mouth_run * (1 - (z + 0.1) / P.mouth_rise)  # the slab's top, where the hole is narrowest
    hat, body, nose = Mesh.union(gnome.hat(P)), Mesh.union(gnome.body(P)), gnome.nose(P)
    for m, size in ((hat, 2 * P.head_r), (body, P.hole_d), (nose, 2 * P.peg_r)):
        assert hole_width(m, z) == pytest.approx(size + flare, abs=0.03)
        assert hole_width(m, P.mouth_rise + 0.1) == pytest.approx(size, abs=0.03)


def hole_width(m: Mesh, z: float) -> float:
    """The gap across the axis in a slab from z to z + 0.1."""
    pieces = sorted((m & slab(z)).solids(), key=lambda s: s.bounding_box().min.X)
    return pieces[1].bounding_box().min.X - pieces[0].bounding_box().max.X
