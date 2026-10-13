import itertools
import math

import pytest
from build123d import Mesher
from shapely.geometry import Point

from grover import render as R
from grover import vector as V
from grover.build import three_mf
from grover.model import COLORS, bodies
from grover.params import P
from grover.trace import maps


@pytest.fixture(scope="module")
def b():
    return bodies(P)


@pytest.fixture(scope="module")
def lay():
    return V.layout(maps(P), P)


def _bbox(b):
    from build123d import Compound

    return Compound(children=list(b.values())).bounding_box()


def test_all_four_colors_present_and_valid(b):
    assert set(b) == set(COLORS)
    for c, body in b.items():
        assert body.is_valid, c
        assert body.volume > 10, c


def test_flat_on_bed_and_size(b):
    bb = _bbox(b)
    assert bb.min.Z == pytest.approx(0, abs=1e-6)
    assert bb.max.Z == pytest.approx(max(P.zone_top.values()), abs=1e-6)
    assert bb.size.X == pytest.approx(P.width, abs=0.6)
    assert bb.size.X < P.bed - P.bed_margin and bb.size.Y < P.bed - P.bed_margin


def test_z_levels_are_whole_layers():
    for z in [P.back_t, P.core_top, *P.zone_top.values()]:
        assert round(z / P.layer, 6) == pytest.approx(round(z / P.layer), abs=1e-6), z


def test_colors_never_overlap(b):
    for (c1, a), (c2, d) in itertools.combinations(b.items(), 2):
        ba, bd = a.bounding_box(), d.bounding_box()
        if any(ba.max.__getattribute__(k) < bd.min.__getattribute__(k) or
               bd.max.__getattribute__(k) < ba.min.__getattribute__(k) for k in "XYZ"):
            continue
        assert (a & d).volume < 0.05, f"{c1} overlaps {c2}"


def test_one_connected_piece(b):
    parts = list(b.values())
    u = parts[0].fuse(*parts[1:])
    assert len(u.solids()) == 1


def test_everything_sits_on_the_core(lay):
    """No overhangs: every raised patch lies over the core footprint."""
    core = lay["silhouette"]
    for f, z, g in lay["top"]:
        assert g.difference(core.buffer(1e-3)).area < 1e-3, (f, z)


def test_top_surface_has_no_holes(lay):
    assert lay["gaps"] < 0.5  # mm^2 of slivers between colors, all far below a nozzle width


def test_keyring_hole_size_and_wall(lay):
    m = maps(P)
    c = Point(*m.hole_mm)
    sil = lay["silhouette"]
    assert not sil.contains(c), "hole is open"
    # hole diameter: nothing within hole_r of center
    assert sil.distance(c) == pytest.approx(P.hole_r, abs=0.02)
    # plastic between hole and outer edge
    outer = max(sil.geoms, key=lambda g: g.area).exterior
    assert outer.distance(c) - P.hole_r >= P.hole_wall - 0.05


def test_hole_through_all_bodies(b):
    from build123d import Cylinder, Pos

    m = maps(P)
    probe = Pos(*m.hole_mm, 2.5) * Cylinder(P.hole_r - 0.05, 6)
    for c, body in b.items():
        assert (body & probe).volume < 1e-3, c


def test_no_features_thinner_than_nozzle(lay):
    """Seen from the top, every color patch survives a 0.3 mm erosion (a 0.4 nozzle can lay it)."""
    from shapely.ops import unary_union

    for f in COLORS:
        g = V._multi(unary_union([x for c, _, x in lay["top"] if c == f]).buffer(0.01))
        for piece in g.geoms:
            if piece.area < 0.05:
                continue
            assert not piece.buffer(-0.15).is_empty, (f, piece.representative_point())


def test_qr_scans_from_back(b, tmp_path):
    path = tmp_path / "back.png"
    R.flat(b, str(path), up=False)
    assert R.decode_qr(str(path)) == P.url


def test_qr_fits_inside_badge(lay):
    panel, _ = V.qr_shapes(P)
    assert lay["silhouette"].buffer(1e-3).contains(panel.buffer(1.0))


def test_3mf_export(tmp_path):
    path = three_mf(tmp_path / "k.3mf")
    assert path.stat().st_size > 50_000
    m = Mesher()
    shapes = m.read(str(path))
    assert len(shapes) == len(COLORS)
