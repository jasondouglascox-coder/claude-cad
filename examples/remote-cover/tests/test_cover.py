"""Test first: each cover prints flat, one solid, the pocket's outline less its clearance, tabs flush with the inside
face over the slots, and a plug concentric with the tongue's round end. Expectations come from params.

Print orientation: the outside face on the bed (Z = 0), the inside face up at Z = t, the ear toward +Y."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.settings import settings
from remote_cover import build
from remote_cover.params import P, Params
from remote_cover.parts import cover


@pytest.fixture(scope="module", params=P.ladder(), ids=lambda q: f"tip{q.ear_tip}")
def part(request):
    q = request.param
    return q, cover(q)


def pieces(part, x=None, y=None, z=(0, 10)):
    """A thin probe across the part: along X at height y, or along Y at x; bounding boxes of the pieces it cuts."""
    z0, z1 = z
    if y is not None:
        probe = Pos(-50, y - 0.05, z0) * Box(200, 0.1, z1 - z0, align=(Align.MIN,) * 3)
    else:
        probe = Pos(x - 0.05, -50, z0) * Box(0.1, 200, z1 - z0, align=(Align.MIN,) * 3)
    return sorted((s.bounding_box() for s in (part & probe).solids()), key=lambda b: (b.min.X, b.min.Y))


PLATE = (0.1, 0.5)  # a slice of the plate below the tabs, the plug and the engraving


def test_prints_flat_one_solid_watertight_on_layers(part):
    q, c = part
    assert printable_problems(c, q.printer) == []
    assert open_edges(c) == 0
    assert off_layer_z(c, q.printer) == []


def test_only_overhangs_are_the_two_tabs(part):
    """The tabs sit flush with the inside face, so their undersides print over air, one each."""
    q, c = part
    got = sorted(downward_faces(c))
    assert [z for z, _ in got] == pytest.approx([q.t - q.tab_t] * 2)
    assert [a for _, a in got] == pytest.approx([q.tab_w * q.tab_out] * 2, abs=1e-3)


def test_fills_the_pocket_less_the_clearance(part):
    q, c = part
    k = q.clearance
    (b,) = pieces(c, y=q.y0 + q.pocket_h / 2, z=PLATE)
    assert (b.min.X, b.max.X) == pytest.approx((k, q.pocket_w - k), abs=0.02)
    (b,) = pieces(c, x=q.pocket_r + 1, z=PLATE)  # beside the tabs and the ear
    assert (b.min.Y, b.max.Y) == pytest.approx((q.y0 + k, q.top - k), abs=0.02)


def test_ear_fills_its_recess(part):
    q, c = part
    k = q.clearance
    (b,) = pieces(c, y=q.top + q.shoulder_r + 0.3, z=PLATE)  # the ear's straight part, below the hole
    assert (b.min.X, b.max.X) == pytest.approx((q.cx - q.ear_w / 2 + k, q.cx + q.ear_w / 2 - k), abs=0.02)
    assert c.bounding_box().max.Y == pytest.approx(q.top + q.ear_tip - k, abs=0.02)


def test_plug_and_hole_concentric_with_the_tongues_round_end(part):
    """The indent is the recess's round end, centered on the insert: the plug sits right at the tongue's tip."""
    q, c = part
    tip = c.bounding_box().max.Y
    assert tip - q.hole_y == pytest.approx(q.ear_w / 2 - q.clearance, abs=0.02)


def test_screw_hole_over_the_insert_through_ear_and_plug(part):
    q, c = part
    for z in (PLATE, (q.t + 0.1, q.t + q.plug_h - 0.3)):
        a, b = pieces(c, y=q.hole_y, z=z)
        assert b.min.X - a.max.X == pytest.approx(q.hole_d, abs=0.05)
        assert (a.max.X + b.min.X) / 2 == pytest.approx(q.cx, abs=0.02)


def test_plug_size_and_height(part):
    q, c = part
    a, b = pieces(c, y=q.hole_y, z=(q.t + 0.05, q.t + 0.15))
    assert (a.min.X, b.max.X) == pytest.approx((q.cx - q.plug_d / 2, q.cx + q.plug_d / 2), abs=0.02)
    assert c.bounding_box().max.Z == pytest.approx(q.t + q.plug_h, abs=1e-6)


def test_tabs_over_the_slots_flush_with_inside_face(part):
    q, c = part
    k = q.clearance
    got = pieces(c, y=q.y0 + k - q.tab_out / 2)
    assert [x for b in got for x in (b.min.X, b.max.X)] == pytest.approx([x for xs in q.tab_xs() for x in xs],
                                                                        abs=0.02)
    for b in got:
        assert (b.min.Z, b.max.Z) == pytest.approx((q.t - q.tab_t, q.t), abs=1e-6)
    assert c.bounding_box().min.Y == pytest.approx(q.y0 + k - q.tab_out, abs=1e-6)


def test_tabs_are_spaced_like_the_slots():
    (a0, a1), (b0, b1) = P.tab_xs()
    assert (b0 + b1) / 2 - (a0 + a1) / 2 == pytest.approx(abs(P.tab_dx[1] - P.tab_dx[0]))


def test_tongue_length_engraved_on_inside_face(part):
    q, c = part
    assert cover(q, mark=False).volume - c.volume > 0.1
    lowest = min(f.center().Z for f in c.faces() if f.normal_at().Z > 1 - 1e-9 and f.center().Z > 0.01)
    assert lowest == pytest.approx(q.t - q.mark_depth, abs=1e-6)


def test_bad_params_are_refused():
    with pytest.raises(ValueError, match="plug_d"):
        Params(plug_d=6.0)
    with pytest.raises(ValueError, match="ear_tip"):
        Params(ear_tip=3.5)
    with pytest.raises(ValueError, match="tab_t"):
        Params(tab_t=2.0)
    with pytest.raises(ValueError, match="corner"):
        Params(tab_dx=(-12.5, 4.8))


def test_build_writes_one_gray_plate_of_the_ladder(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "step" / "remote_cover.step").exists()
    assert (tmp_path / "render" / "iso.png").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"remote_cover{s.project_suffix}")}
    assert got == {build.name(q): settings().filament(P.filament_gray) for q in P.ladder()}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_gray_only(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"remote_cover{s.project_suffix}"
    back = s.roundtrip(plate)
    assert s.same_objects(back, plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_gray),)]
