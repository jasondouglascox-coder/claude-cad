"""The rose, in two sizes: the 8" one, and a 4" one printed four to a plate (`small`: walls, gaps and the nail stay
full size, so its centre has fewer, taller petals that lean together and a nub in the middle). Each is one solid
flat on the bed, curved petals with pointed tips, a funnel centre that needs no supports, PETG-interface supports
under the curled outer petals only, and a keyhole that hangs it by its centre."""
import math

import numpy as np
import pytest
from build123d import Align, Box, Pos

from cadkit.checks import downward_faces, off_layer_z, overhangs, printable_problems
from cadkit.render import heights
from rose_wall import flower, petals
from rose_wall.params import P, SMALL, small

MIN = (Align.MIN, Align.MIN, Align.MIN)
ROSES = pytest.mark.parametrize("p", [P, SMALL], ids=["8in", "small"])


def probe(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=MIN)


def test_small_is_half_the_rose_with_full_size_walls_gaps_and_nail():
    """Halving the walls would leave two lines; halving the gaps would fuse them; the nail is the same nail."""
    assert SMALL.diameter == pytest.approx(P.diameter / 2)
    assert SMALL.foot_r == pytest.approx(P.foot_r / 2)
    assert SMALL.length == pytest.approx(tuple(x / 2 for x in P.length))
    assert (SMALL.wall, SMALL.centre_gap, SMALL.petals) == (P.wall, P.centre_gap, P.petals)
    assert SMALL.centre_r == pytest.approx(P.centre_r / 2)  # fewer centre petals fill half the radius
    assert small(P) == SMALL


def test_petal_sides_rise_upright_then_lean_out_to_their_tip():
    line = petals.side(30.0, 120.0, P.bend)
    assert line[0][2] == 0 and math.degrees(line[1][2]) < 2.0  # starts upright
    assert math.degrees(line[-1][2]) == pytest.approx(120.0)
    assert all(b[2] >= a[2] for a, b in zip(line, line[1:]))  # the lean only grows: it curves out, never back in
    assert math.hypot(line[-1][0], line[-1][1]) < 30.0  # bent, so the tip is nearer the foot than the length


@ROSES
def test_only_the_outer_petals_curl_past_45_degrees(p):
    """The centre and the innermost outer petals print without supports; the curl is the outer petals'."""
    assert p.centre_lean[1] + p.centre_lip <= 45.0 and p.centre_lean[0] + p.centre_lip <= 45.0
    assert p.lean[0] <= 45.0 < p.lean[1]


@ROSES
def test_centre_is_a_funnel(p):
    """Centre petal rims step down toward the middle: you look down into it, like a real rose."""
    rims = [petals.centre_line(p, k)[-1][1] for k in range(p.centre_petals)]
    assert all(b > a for a, b in zip(rims, rims[1:]))
    assert rims[-1] - rims[0] >= p.centre_drop * 0.9
    assert rims[0] > p.base_t  # every centre petal stands up out of the base


@ROSES
def test_centre_petals_never_touch(p):
    """A gap between neighbouring centre petals' feet: the dark lines of the funnel."""
    for k in range(p.centre_petals - 1):
        assert petals.centre_foot(p, k + 1) - (petals.centre_foot(p, k) + p.wall) == pytest.approx(p.centre_gap)
        assert petals.centre(p, k).distance_to(petals.centre(p, k + 1)) > 0  # leaning together, they still don't
    assert petals.outer_foot(p, 0) == pytest.approx(p.centre_r)


@ROSES
@pytest.mark.parametrize("k", [0, -1])
def test_centre_petals_print_without_supports(p, k):
    assert overhangs(petals.centre(p, k % p.centre_petals)) == []


def test_small_nub_plugs_the_middle_below_the_innermost_rim():
    top = flower.nub_top(SMALL)
    assert SMALL.printer.on_layer(top) and SMALL.base_t < top < petals.centre_line(SMALL, 0)[-1][1]
    assert overhangs(flower.nub(SMALL)) == []
    assert flower.nub(P) is None  # the 8" rose's deep funnel needs none


def floor_showing(p) -> float:
    """Looking straight at the rose, how much of its centre (inside the outer petals' feet) is the base's flat top."""
    r_max, step = p.centre_r + 4, 0.05
    h = heights(flower.parts(p), ((-r_max, -r_max), (r_max, r_max)), step=step)
    n = h.shape[0]
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) * step - r_max
    return float((h <= p.base_t + 0.05)[np.hypot(xx, yy) < p.centre_r].mean())


def test_small_centre_is_filled_in():
    """The user, on the first small rose: fill in the middle so you don't see the floor. At half size the base is
    only a few mm under the centre rims, so it reads as a floor, not as depth: the centre petals keep their backs,
    stand taller and lean together so you can't see down between them (78% of the centre was floor, now ~21%)."""
    assert floor_showing(SMALL) <= 0.25


@pytest.fixture(scope="module", params=[P, SMALL], ids=["8in", "small"])
def rose(request):
    return request.param, flower.make(request.param)


def flat_faces_off_layer(p, rose):
    """(radius from the centre, z) of every horizontal face whose z isn't a layer."""
    cx, cy = flower.centre_xy(p)
    zs = set(off_layer_z(rose, p.printer))
    return [(math.hypot(f.center().X - cx, f.center().Y - cy), round(f.center().Z, 4)) for f in rose.faces()
            if abs(abs(f.normal_at().Z) - 1) < 1e-9 and round(f.center().Z, 4) in zs]


@pytest.mark.whole
def test_one_solid_flat_on_the_bed(rose):
    p, rose = rose
    assert printable_problems(rose, p.printer) == []
    bb = rose.bounding_box()
    assert max(bb.size.X, bb.size.Y) == pytest.approx(p.diameter, abs=4.0)
    # every designed flat is on a layer; the small rose's petals, fusing near their crests, leave a few mm2 nearly
    # flat under a curl, out past the feet, where the PETG-interface supports hold it anyway
    reach = max(petals.outer_foot(p, i) for i in range(p.petals)) + p.wall
    assert all(r > reach for r, _ in flat_faces_off_layer(p, rose))


@pytest.mark.whole
def test_no_floor_lip_past_the_petals(rose):
    """Cut off at the bed, a rose has no lip: along every direction, the outermost material at the floor's height
    is a petal's foot, never floor sticking out past it."""
    from build123d import Rot
    p, rose = rose
    cx, cy = flower.centre_xy(p)
    for k in range(24):
        a = 360 * k / 24 + 3.0
        ray = Pos(cx, cy, 0) * Rot(0, 0, a) * probe(0, -0.05, p.floor / 2, p.diameter, 0.1, 0.1)
        reach = max((Rot(0, 0, -a) * Pos(-cx, -cy, 0) * s).bounding_box().max.X for s in (rose & ray).solids())
        assert reach == pytest.approx(petals.foot_reach(p, a), abs=0.3), a


@pytest.mark.whole
def test_keyhole_hangs_it_by_its_centre(rose):
    """The nail's shank rests against the top of the slot, at the flower's centre; the head sits under a lip with
    solid material over its roof."""
    p, rose = rose
    cx, cy = flower.centre_xy(p)
    line = rose & probe(cx - 0.05, cy - 30, p.key_lip / 2, 0.1, 60, 0.1)
    above = [s.bounding_box() for s in line.solids() if s.bounding_box().min.Y > cy - 1]
    top = min(b.min.Y for b in above)  # the first material above the slot
    assert top - cy == pytest.approx(flower.NAIL_D / 2, abs=0.05)
    assert p.base_t - flower.key_top(p) >= 1.6  # roof over the nail head
    # the only bridge in the base: the roof's strip
    inside = [z for z, _ in downward_faces(rose) if z < p.base_t]
    assert inside and all(z == pytest.approx(flower.key_top(p)) for z in inside)


@pytest.mark.whole
@ROSES
def test_plate_opens_red_with_petg_supports(p, tmp_path):
    import json, zipfile
    from cadkit import bambu3mf, slicers
    flower.write(p, tmp_path)
    s = slicers.active()
    path = tmp_path / "plates" / f"{p.name}{s.project_suffix}"
    assert [f for _, f, _ in s.read_filaments(path)] == [p.slot_rose] * p.per_plate
    # review: a flat keyhole roof gets tree support filling the nail's pocket, trapped behind the lip; a blocker on
    # every rose keeps it out
    assert bambu3mf.read_blockers(path) == {name: [f"{name} blocker"] for name, _, _ in s.read_filaments(path)}
    cfg = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    assert cfg["enable_support"] == "1" and cfg["support_interface_filament"] == str(p.slot_support)
    # the user: "supports are not set" in Bambu Studio's window, which applies only the settings this lists
    # (the ones that differ from the preset)
    preset = json.loads(bambu3mf.SETTINGS.read_text())
    listed = set(cfg["different_settings_to_system"][0].split(";"))
    support = {k for k in cfg if k.startswith("support_") or k == "enable_support"}
    changed = {k for k in support if cfg[k] != preset[k]}
    assert "enable_support" in changed and changed <= listed
    assert cfg["filament_type"][p.slot_support - 1] == "PETG"
    # review: tree trunks stand on the floor between petals with no PETG under them, so leave a layer's gap there;
    # and keep the support under the smallest curl tips (the slicer drops "small" overhangs, leaving one in air)
    assert cfg["support_bottom_z_distance"] == str(p.printer.layer)
    assert cfg["support_remove_small_overhang"] == "0"
    # the prime tower clears every rose
    x, y, w = float(cfg["wipe_tower_x"][0]), float(cfg["wipe_tower_y"][0]), float(cfg["prime_tower_width"])
    for cx, cy in flower.spots(p):
        near = math.hypot(max(x - cx, 0, cx - (x + w)), max(y - cy, 0, cy - (y + w)))
        assert near >= p.diameter / 2 + 3.0


def test_four_small_roses_fit_the_bed_apart():
    spots = flower.spots(SMALL)
    assert len(spots) == SMALL.per_plate == 4
    half = SMALL.diameter / 2 + 2.0  # the bounding box runs ~1.5 mm past the nominal diameter
    for i, (x, y) in enumerate(spots):
        assert half <= x <= SMALL.printer.bed - half and half <= y <= (SMALL.printer.bed_y or SMALL.printer.bed) - half
        for x2, y2 in spots[i + 1:]:
            assert math.hypot(x2 - x, y2 - y) >= 2 * half + 10.0  # room for the supports between them


@pytest.mark.slow
@ROSES
def test_slicer_supports_the_curls_with_petg(p, tmp_path):
    from cadkit import slicers
    s = slicers.active()
    if not s.available():
        pytest.skip("needs a slicer")
    flower.write(p, tmp_path)
    report = s.slice_report(tmp_path / "plates" / f"{p.name}{s.project_suffix}", tmp_path / "s.3mf")
    used = {f for r in report["layers"] for f in r[0]}
    assert used == {p.slot_rose, p.slot_support}
    assert report["grams"][p.slot_support] < report["grams"][p.slot_rose] / 5  # PETG only at the interface
    if s.name == "bambu":  # the G-code: no support anywhere in a keyhole's pocket
        from cadkit import bambu, gcode
        x0, y0, x1, y1 = flower.pocket(p)
        inside = [(round(z, 2), cx, cy) for cx, cy in flower.spots(p)
                  for ax, ay, bx, by, z, f in gcode.extrusions(bambu.plate_gcode(tmp_path / "s.3mf"))
                  if f.startswith("Support") and z <= flower.key_top(p)
                  and x0 <= (ax + bx) / 2 - cx <= x1 and y0 <= (ay + by) / 2 - cy <= y1]
        assert inside == []
