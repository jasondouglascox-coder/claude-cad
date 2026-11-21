"""Test first: each cover prints flat, one solid, the original's outline (less the fit), tabs flush with the
inside face, and a plug of its ladder size round the screw hole. Expectations come from params.

Print orientation: the outside face on the bed (Z = 0), the inside face up at Z = t, the ear toward +Y."""
import pytest
from build123d import Align, Box, Pos

from cadkit import slicers
from cadkit.checks import downward_faces, off_layer_z, open_edges, printable_problems
from cadkit.settings import settings
from remote_cover import build
from remote_cover.params import P, Params
from remote_cover.parts import cover


@pytest.fixture(scope="module", params=P.plug_ds)
def part(request):
    return request.param, cover(P, request.param)


def pieces(part, x=None, y=None, z=(0, 10)):
    """A thin probe across the part: along X at height y, or along Y at x; bounding boxes of the pieces it cuts."""
    z0, z1 = z
    if y is not None:
        probe = Pos(-50, y - 0.05, z0) * Box(200, 0.1, z1 - z0, align=(Align.MIN,) * 3)
    else:
        probe = Pos(x - 0.05, -50, z0) * Box(0.1, 200, z1 - z0, align=(Align.MIN,) * 3)
    return sorted((s.bounding_box() for s in (part & probe).solids()), key=lambda b: (b.min.X, b.min.Y))


def test_prints_flat_one_solid_watertight_on_layers(part):
    _, c = part
    assert printable_problems(c, P.printer) == []
    assert open_edges(c) == 0
    assert off_layer_z(c, P.printer) == []


def test_only_overhangs_are_the_two_tabs(part):
    """The tabs sit flush with the inside face, so their undersides print over air: 1 mm (plus the fit), one each."""
    _, c = part
    got = sorted(downward_faces(c))
    assert [z for z, _ in got] == pytest.approx([P.t - P.tab_t] * 2)
    assert [a for _, a in got] == pytest.approx([P.tab_w * (P.tab_out + P.fit)] * 2, abs=1e-3)


def test_plate_width_length_and_thickness(part):
    _, c = part
    (b,) = pieces(c, y=P.y0 + P.h / 2, z=(0.1, P.t - 0.1))
    assert b.max.X - b.min.X == pytest.approx(P.w - 2 * P.fit, abs=0.02)
    (b,) = pieces(c, x=P.tab_in / 2, z=(0.1, P.t - 0.1))  # beside the tabs
    assert b.max.Y - b.min.Y == pytest.approx(P.h - 2 * P.fit, abs=0.02)
    bb = c.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6)


def test_ear_round_end_and_width(part):
    _, c = part
    (b,) = pieces(c, y=P.hole_y - P.hole_d, z=(0.1, P.t - 0.1))  # the ear's straight part, below the hole
    assert len(pieces(c, y=P.hole_y, z=(0.1, P.t - 0.1))) == 2  # the hole splits the ear
    assert b.max.X - b.min.X == pytest.approx(P.ear_w - 2 * P.fit, abs=0.05)
    assert c.bounding_box().max.Y == pytest.approx(P.y0 + P.h + P.ear_len - P.fit, abs=0.02)
    assert (b.min.X + b.max.X) / 2 == pytest.approx(P.hole_x, abs=0.02)


def test_screw_hole_goes_through_ear_and_plug(part):
    _, c = part
    for z in ((0.1, P.t - 0.1), (P.t + 0.1, P.t + P.plug_h - 0.3)):
        a, b = pieces(c, y=P.hole_y, z=z)
        assert b.min.X - a.max.X == pytest.approx(P.hole_d, abs=0.05)


def test_plug_size_and_height(part):
    d, c = part
    a, b = pieces(c, y=P.hole_y, z=(P.t + 0.05, P.t + 0.15))
    assert b.max.X - a.min.X == pytest.approx(d, abs=0.02)
    assert (a.min.X + b.max.X) / 2 == pytest.approx(P.hole_x, abs=0.02)
    assert c.bounding_box().max.Z == pytest.approx(P.t + P.plug_h, abs=1e-6)


def test_tabs_flush_with_inside_face(part):
    _, c = part
    got = pieces(c, y=P.tab_out / 2)
    assert [x for b in got for x in (b.min.X, b.max.X)] == pytest.approx(
        [x for xs in P.tab_xs() for x in xs], abs=0.02)
    for b in got:
        assert (b.min.Z, b.max.Z) == pytest.approx((P.t - P.tab_t, P.t), abs=1e-6)
    assert c.bounding_box().min.Y == pytest.approx(0, abs=1e-6)  # the tab tips


def test_size_engraved_on_inside_face(part):
    """The plug size is cut into the inside face, so the covers can be told apart off the bed."""
    d, c = part
    assert cover(P, d, mark=False).volume - c.volume > 0.2
    lowest = min(f.center().Z for f in c.faces() if f.normal_at().Z > 1 - 1e-9 and f.center().Z > 0.01)
    assert lowest == pytest.approx(P.t - P.mark_depth, abs=1e-6)


def test_bad_params_are_refused():
    with pytest.raises(ValueError, match="plug_ds"):
        Params(plug_ds=(6.0,))
    with pytest.raises(ValueError, match="tab_t"):
        Params(tab_t=2.0)


def test_build_writes_one_gray_plate_of_the_ladder(tmp_path):
    assert build.main(["--out", str(tmp_path)]) == 0
    assert (tmp_path / "step" / "remote_cover.step").exists()
    assert (tmp_path / "render" / "iso.png").exists()
    s = slicers.active()
    got = {n: f for n, f, _ in s.read_filaments(tmp_path / "plates" / f"remote_cover{s.project_suffix}")}
    assert got == {build.name(d): settings().filament(P.filament_gray) for d in P.plug_ds}


@pytest.mark.skipif(not slicers.active().available(), reason="no slicer installed (settings: slicer)")
def test_slicer_slices_it_in_gray_only(tmp_path):
    build.main(["--out", str(tmp_path)])
    s = slicers.active()
    plate = tmp_path / "plates" / f"remote_cover{s.project_suffix}"
    back = s.roundtrip(plate)
    assert s.same_objects(back, plate)
    report = s.slice_report(plate, tmp_path / "s.3mf")
    assert [r[0] for r in report["layers"]] == [(settings().filament(P.filament_gray),)]
