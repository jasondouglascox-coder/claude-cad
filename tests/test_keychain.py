import itertools
import math

import pytest
from build123d import Mesher
from shapely.geometry import Point

from grover import render as R
from grover import vector as V
from grover.build import three_mf
from grover.design import design
from grover.model import COLORS, bodies
from grover.params import P


@pytest.fixture(scope="module")
def b():
    return bodies(P)


@pytest.fixture(scope="module")
def d():
    return design(P)


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
    assert bb.size.X == pytest.approx(P.width - 2 * P.tail_in, abs=0.6)  # tails pulled in
    assert bb.size.X < P.bed - P.bed_margin and bb.size.Y < P.bed - P.bed_margin


def test_z_levels_are_whole_layers():
    for z in [P.back_t, P.core_top, *P.zone_top.values(),
              P.zone_top["ring"] - P.ring_sink, P.zone_top["banner"] + P.letter_raise]:
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


def test_everything_sits_on_the_core(d):
    """No overhangs: every raised patch lies over the core footprint."""
    for f, z, g in d.pieces:
        assert g.difference(d.silhouette.buffer(1e-3)).area < 1e-3, (f, z)


def test_top_surface_tiles_the_silhouette(d):
    from shapely.ops import unary_union

    top = unary_union([g for _, _, g in d.pieces])
    assert d.silhouette.difference(top).area < 0.05  # mm^2: no cracks between colors
    total = sum(g.area for _, _, g in d.pieces)
    assert total - top.area < 0.05  # and no double-claimed area


def test_keyring_hole_size_and_wall(d):
    c = Point(*d.hole[:2])
    sil = d.silhouette
    assert not sil.contains(c), "hole is open"
    # hole diameter: nothing within hole_r of center
    assert sil.distance(c) == pytest.approx(P.hole_r, abs=0.02)
    # plastic between hole and outer edge
    outer = max(sil.geoms, key=lambda g: g.area).exterior
    assert outer.distance(c) - P.hole_r >= P.hole_wall - 0.05


def test_hole_through_all_bodies(b, d):
    from build123d import Cylinder, Pos

    probe = Pos(*d.hole[:2], 2.5) * Cylinder(P.hole_r - 0.05, 6)
    for c, body in b.items():
        assert (body & probe).volume < 1e-3, c


def test_no_features_thinner_than_nozzle(d):
    """Seen from the top, every color patch survives a 0.3 mm erosion (a 0.4 nozzle can lay it)."""
    from shapely.ops import unary_union

    for f in COLORS:
        g = V._multi(unary_union([x for c, _, x in d.pieces if c == f]).buffer(0.01))
        for piece in g.geoms:
            if piece.area < 0.05:
                continue
            assert not piece.buffer(-0.15).is_empty, (f, piece.representative_point())


def test_qr_scans_from_back(b, tmp_path):
    path = tmp_path / "back.png"
    R.flat(b, str(path), up=False)
    assert R.decode_qr(str(path)) == P.url


def test_qr_fits_inside_badge(d):
    panel, _ = V.qr_shapes(P)
    assert d.silhouette.buffer(1e-3).contains(panel.buffer(1.0))


def test_eyes_are_circles_of_equal_size(d):
    assert len(d.eyes) == 2
    (x1, y1, r1), (x2, y2, r2) = d.eyes
    assert r1 == pytest.approx(r2, rel=0.1)
    assert abs(y1 - y2) < 0.5  # level
    brown_eye = [g for f, _, g in d.pieces if f == "brown"]
    from shapely.ops import unary_union
    from shapely.geometry import Point as Pt

    br = unary_union(brown_eye)
    for x, y, r in d.eyes:  # the eye disc is brown + white glints, nothing else
        disc = Pt(x, y).buffer(r - 0.05)
        whites = unary_union([g for f, _, g in d.pieces if f == "white"]).intersection(disc).area
        assert br.intersection(disc).area + whites == pytest.approx(disc.area, rel=0.02)


def test_letters_and_paw_prints_clear_of_outlines(d):
    """Letters and paw prints keep detail_gap of base color from the generated outline."""
    for zone in ("banner", "ring"):
        vis, h = d.zones[zone], P.zone_top[zone]
        edge = vis.boundary
        brown = [g for f, z, gs in d.pieces if f == "brown" and z >= h
                 for g in gs.geoms if vis.buffer(-1e-3).contains(g.representative_point())]
        outline = [g for g in brown if g.distance(edge) < 1e-3]
        details = [g for g in brown if g.distance(edge) >= 1e-3]
        assert details, zone
        for g in details:
            gap = min(g.distance(o) for o in outline)
            assert gap >= P.detail_gap - 0.02, (zone, g.centroid, gap)


def test_sketch_parts_found(d):
    from grover.sketch import load

    k = load(round(d.ring[0], 6))
    assert len(k.paws) == 2 and len(k.eyes) == 2
    assert k.nose.area > 2.0
    for x, y, _ in k.glints:  # every glint sits inside an eye
        assert any(math.hypot(x - ex, y - ey) < er for ex, ey, er in k.eyes)


def test_ribbon_sketch_lands_on_the_artwork():
    from shapely.ops import unary_union

    from grover import sketch
    from grover.trace import ZONES, maps

    m = maps(P)
    traced = V.mask_polys((m.zone == ZONES.index("banner") + 1) | (m.zone == ZONES.index("tail") + 1), m, P)
    # same frame as the sketch registration: compare after centering both on their bounds
    rb = sketch.load_ribbon(design(P).zones["banner"].wkt)  # registers onto any target; reuse design's own
    d = design(P)
    ribbon = unary_union([d.zones["banner"], d.zones["tail"]])
    assert ribbon.area > 0.9 * traced.area  # nothing lost in registration
    left, right = rb.tails
    assert abs(left.area - right.area) / right.area < 0.01  # mirrored tails


def test_relief_details(d):
    """Ring paw prints stand above the sunk orange; eyes/nose at paw height; letters above the ribbon."""
    tops = {(f, z) for f, z, _ in d.pieces}
    ring, banner, paw = P.zone_top["ring"], P.zone_top["banner"], P.zone_top["paw"]
    assert ("orange", ring - P.ring_sink) in tops and ("brown", ring) in tops
    assert ("brown", banner + P.letter_raise) in tops
    eyes = [g for f, z, g in d.pieces if f == "brown" and z == paw]
    assert eyes and sum(x.area for x in eyes) > 2 * 3.0  # two eye discs + nose
