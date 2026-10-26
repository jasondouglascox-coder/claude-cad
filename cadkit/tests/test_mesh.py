"""Meshes stand in for shapes where B-rep booleans give up: unioned exactly (manifold3d), and accepted by the
checks, the renders and the plate writer like any part."""
import numpy as np
import pytest

pytest.importorskip("manifold3d")
from build123d import Color

from cadkit import checks
from cadkit.mesh import Mesh
from conftest import box


def test_from_shape_keeps_volume_and_bounds():
    m = Mesh.from_shape(box(0, 0, 0, 10, 20, 3))
    assert m.is_valid and m.volume == pytest.approx(600, rel=1e-6)
    bb = m.bounding_box()
    assert (bb.min.X, bb.max.Y, bb.size.Z) == pytest.approx((0, 20, 3))


def test_union_of_overlapping_bodies_is_one_solid():
    a, b = Mesh.from_shape(box(0, 0, 0, 10, 10, 2)), Mesh.from_shape(box(5, 5, 0, 10, 10, 4))
    u = Mesh.union([a, b])
    assert len(u.solids()) == 1 and u.volume == pytest.approx(200 + 400 - 50)
    apart = Mesh.union([a, Mesh.from_shape(box(30, 0, 0, 5, 5, 5))])
    assert len(apart.solids()) == 2


def test_trim_cuts_below_a_height_and_translate_moves():
    m = Mesh.from_shape(box(0, 0, -1, 10, 10, 3)).trimmed(0.0).translate((5, 0, 0))
    bb = m.bounding_box()
    assert m.volume == pytest.approx(200) and bb.min.Z == pytest.approx(0) and bb.min.X == pytest.approx(5)


def test_centroid_is_the_centre_of_mass():
    """Where a mesh balances: what a wall piece hangs plumb under."""
    a = Mesh.from_shape(box(0, 0, 0, 10, 10, 2))  # 200 mm3 centred at (5, 5, 1)
    b = Mesh.from_shape(box(20, 0, 0, 10, 10, 6))  # 600 mm3 centred at (25, 5, 3)
    assert Mesh.union([a, b]).centroid == pytest.approx((20, 5, 2.5))


def test_simplify_clears_slivers_a_union_leaves():
    """Bodies whose faces nearly line up union into steps thinner than open_edges' rounding; simplify collapses them
    without moving the shape."""
    a, b = Mesh.from_shape(box(0, 0, 0, 10, 10, 2)), Mesh.from_shape(box(5.00003, 0.00003, 0, 10, 10, 2.00003))
    u = Mesh.union([a, b])
    assert checks.open_edges(u) > 0
    s = u.simplify()
    assert checks.open_edges(s) == 0 and s.volume == pytest.approx(u.volume, rel=1e-5)
    low = s.verts[:, 2] < 1e-3
    assert low.any() and (s.verts[low, 2] == 0).all()  # what stood on the bed still does, exactly


def test_from_grid_closes_two_skins_into_a_solid():
    """Two skins as [column][row] point grids with rows lined up close into a watertight solid, whichever way the
    skins run."""
    xs, ys = np.meshgrid(np.linspace(0, 10, 6), np.linspace(0, 4, 5), indexing="ij")
    top = np.stack([xs, ys, np.full_like(xs, 2.0)], axis=2)
    under = top.copy()
    under[..., 2] = 0.0
    for a, b in ((top, under), (under, top)):
        m = Mesh.from_grids(a, b)
        assert m.is_valid and m.volume == pytest.approx(80) and checks.open_edges(m) == 0


def test_checks_accept_meshes():
    from cadkit.printer import Printer
    pr = Printer()
    on_bed = Mesh.from_shape(box(10, 10, 0, 10, 10, 2.2))
    assert checks.printable_problems(on_bed, pr) == []
    assert checks.off_layer_z(on_bed, pr) == []  # 2.2 is on 0.2 mm layers
    unioned = Mesh.union([Mesh.from_shape(box(80, 80, 0, 10, 10, 61.4)), Mesh.from_shape(box(85, 80, 0, 10, 10, 61.4))])
    assert checks.off_layer_z(unioned, pr) == []  # stored in float32 (61.4000015): still on its layer
    assert checks.off_layer_z(Mesh.from_shape(box(10, 10, 0, 5, 5, 2.25)), pr) == [2.25]
    floating = Mesh.union([on_bed, Mesh.from_shape(box(12, 12, 4, 3, 3, 1))])
    assert "2 separate solids (expected 1)" in checks.printable_problems(floating, pr)
    assert checks.downward_faces(floating) == [(4.0, 9.0)]
    assert checks.overhangs(floating) == [(4.0, 9.0)]  # as for a shape: a flat underside counts too
    lower = Mesh.from_shape(box(0, 0, 0, 10, 10, 2))
    assert checks.unsupported(Mesh.from_shape(box(2, 2, 2, 4, 4, 1)), lower) == pytest.approx(0, abs=1e-6)
    assert checks.unsupported(Mesh.from_shape(box(8, 2, 2, 4, 4, 1)), lower) == pytest.approx(2 * 4 * 0.1, rel=1e-4)


def test_heights_and_render_take_meshes(tmp_path):
    from cadkit.render import heights, render
    m = Mesh.from_shape(box(0, 0, 0, 10, 10, 3))
    h = heights([m], ((-1, -1), (11, 11)), step=1.0)
    assert h[5, 5] == pytest.approx(3) and np.isnan(h[0, 0])
    render([(m, Color(0.9, 0.1, 0.1))], tmp_path / "m.png", px=100)
    assert (tmp_path / "m.png").exists()


def test_a_plate_takes_a_mesh(tmp_path):
    from cadkit import slicers
    from cadkit.export import write_plates
    from cadkit.plates import Plate
    m = Mesh.from_shape(box(50, 50, 0, 10, 10, 2))
    write_plates([Plate("p", 1, [("thing", m)])], tmp_path / "plates", tmp_path / "plates.csv", lambda name: 2)
    s = slicers.active()
    path = tmp_path / "plates" / f"p{s.project_suffix}"
    assert [(n, f) for n, f, _ in s.read_filaments(path)] == [("thing", 2)]
    assert (tmp_path / "plates" / "p.stl").exists()  # a mesh has no STEP: the plate's geometry goes out as STL


def test_mesh_booleans_take_meshes_or_shapes():
    a = Mesh.from_shape(box(0, 0, 0, 10, 10, 2))
    assert (a & box(5, 0, 0, 10, 10, 10)).volume == pytest.approx(100)
    assert (a - box(5, 0, -1, 10, 10, 10)).volume == pytest.approx(100)
    assert (a + Mesh.from_shape(box(10, 0, 0, 5, 10, 2))).volume == pytest.approx(300)
    miss = a & box(50, 50, 0, 1, 1, 1)
    assert miss.volume == 0 and miss.solids() == []


def test_drop_crumbs_keeps_the_real_pieces():
    a = Mesh.from_shape(box(0, 0, 0, 10, 10, 2))
    crumb = Mesh.from_shape(box(30, 0, 0, 0.5, 0.5, 0.5))
    other = Mesh.from_shape(box(50, 0, 0, 5, 5, 5))
    kept = Mesh.union([a, crumb, other]).drop_crumbs(1.0)
    assert sorted(round(s.volume) for s in kept.solids()) == [125, 200]
