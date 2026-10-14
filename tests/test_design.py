"""The 2D design: what the front and back must contain, derived from params and the art."""
import math

import numpy as np
import pytest
import shapely
from shapely.geometry import Point
from shapely.ops import substring, unary_union

from grover import art as A
from grover import back as B
from grover import ears as E
from grover import vec as V
from grover.params import P
from grover.regions import band_regions, design


@pytest.fixture(scope="module")
def d():
    return design(P)


def _opened(g, w):
    return g.buffer(-w / 2).buffer(w / 2)


def test_ear_tips_clear_the_ring_circle(d):
    assert d.figure_top <= d.R - P.circle_w - P.ear_clear
    assert d.figure_top > d.r  # the ears still reach past the backdrop disc, as in the logo


def test_ear_outlines_are_clean_arches(d):
    """Each ear's outer edge runs half a line outside its drawn arch: no bumps left over from the tracing."""
    figure = unary_union([d.ribbon, d.cat_white, d.cat_orange, d.face_ink]).buffer(0.02).buffer(-0.02)
    edge = max(V.multi(figure).geoms, key=lambda g: g.area).exterior
    arches = [arch for arch, _ in E.curves(P)]
    assert len(arches) == 2
    for arch in arches:
        mid = substring(arch, 0.6, arch.length - 0.6)  # the ends join the traced outline
        near = edge.intersection(mid.buffer(P.line_w / 2 + 0.3, cap_style="flat"))
        pts = shapely.get_coordinates(shapely.segmentize(near, 0.05))
        assert len(pts) * 0.05 > 0.9 * mid.length  # the edge runs the whole arch
        off = np.array([arch.distance(Point(q)) for q in pts]) - P.line_w / 2
        assert np.abs(off).max() < 0.05, f"edge {off.min():+.2f}..{off.max():+.2f} mm off the arch"


def _raised(d):
    """Everything above the base band: the face band and the ring's ink."""
    return unary_union([d.ribbon, d.cat_white, d.cat_orange, d.face_ink, d.ring_ink])


def test_neighbouring_colors_touch(d):
    """Raised regions meet without gaps: a gap would show the band below as a thin line between two colors."""
    raised = _raised(d)
    gaps = raised.buffer(0.03).buffer(-0.03).difference(raised)
    assert gaps.area < 0.05, f"{gaps.area:.2f} mm^2 of gaps"


def test_the_base_shows_only_as_the_ring_and_the_disc(d):
    """Where nothing is raised over it, the base band is the orange ring or the white disc: no white rim round the
    figure, and no ledge sticking out past the face band beyond the ring."""
    seen = unary_union([d.base_white, d.base_orange]).difference(_raised(d))
    white_seen = d.base_white.intersection(seen).difference(Point(0, 0).buffer(d.r + 0.05, quad_segs=256))
    assert white_seen.area < 0.01, f"{white_seen.area:.2f} mm^2 of white base seen outside the disc"
    ledge = seen.difference(Point(0, 0).buffer(d.R, quad_segs=256))
    assert ledge.area < 0.01, f"{ledge.area:.2f} mm^2 of base seen beyond the ring"


def test_every_brown_mark_is_at_least_a_line_wide(d):
    for name in ("face_ink", "ring_ink", "top_brown"):
        g = getattr(d, name)
        kept = _opened(g, P.line_w - 0.06).area
        assert kept >= 0.97 * g.area, f"{name}: {g.area - kept:.1f} mm^2 thinner than {P.line_w}"


def test_fills_have_no_tiny_islands(d):
    glint = math.pi * (P.eye_glint_min_d / 2) ** 2 * 0.8
    for name in ("ribbon", "cat_white", "cat_orange", "top_white", "base_white", "base_orange"):
        floor = min(P.min_island, glint) if name == "top_white" else P.min_island
        for piece in getattr(d, name).geoms:
            assert piece.area >= floor, f"{name} piece of {piece.area:.2f} mm^2"


def test_each_band_tiles_without_overlap(d):
    """Regions of one band never overlap; the face band covers the figure with no gaps."""
    bands = {}
    for color, lo, hi, g in band_regions(d):
        bands.setdefault(lo, []).append(g)
    for lo, gs in bands.items():
        total = sum(g.area for g in gs)
        assert unary_union(gs).area == pytest.approx(total, rel=1e-5), f"overlap in band from {lo}"
    face = unary_union([d.ribbon, d.cat_white, d.cat_orange, d.face_ink]).buffer(0.02).buffer(-0.02)
    assert not hasattr(face, "geoms") or len(face.geoms) == 1  # one connected figure
    base = unary_union([d.base_white, d.base_orange])
    assert base.area == pytest.approx(d.silhouette.area, rel=1e-3)


def test_two_eyes_with_glints_and_a_nose_raised(d):
    assert len(d.eyes) == 2
    (x1, y1, r1), (x2, y2, r2) = d.eyes
    assert abs(y1 - y2) < 1.0 and 3 < abs(x1 - x2) < 10 and abs(r1 - r2) < 0.3
    for x, y, r in d.eyes:
        eye = Point(x, y).buffer(r)
        assert d.top_brown.intersection(eye).area > 0.6 * eye.area
        assert d.top_white.intersection(eye).area > 0.1  # glints


def test_the_letters_are_raised_as_separate_glyphs(d):
    ribbon_zone = d.ribbon.buffer(0.5)
    glyphs = [g for g in d.top_brown.geoms if ribbon_zone.contains(g.representative_point())]
    assert len(glyphs) >= len("GROVER&PALS")


def test_two_paws_raised_and_resting_on_white(d):
    paws = sorted(d.paws.geoms, key=lambda g: g.centroid.x)
    assert len(paws) == 2 and all(g.area > P.paw_min_area for g in paws)
    assert paws[0].centroid.x < 0 < paws[1].centroid.x
    for paw in paws:
        white_part = d.top_white.intersection(paw)
        assert white_part.area > 0.5 * paw.area
        assert d.cat_white.buffer(0.03).contains(white_part.buffer(-0.02))  # raised white rests on white


def test_top_band_rests_on_the_face_band(d):
    face = unary_union([d.ribbon, d.cat_white, d.cat_orange, d.face_ink]).buffer(0.03)
    for g in (d.top_white, d.top_brown):
        assert g.difference(face).area < 0.01


def test_hole_sits_in_the_ring_with_its_wall(d):
    x, y, r = d.hole
    assert x == 0 and r == P.hole_d / 2
    assert y + r == pytest.approx(d.R - P.hole_wall)
    assert y - r > d.r + P.circle_w  # the hole itself stays off the disc circle (its brown ring may touch it)


def test_qr_panel_and_url_fit_inside_the_back(d):
    panel, mods = B.qr_shapes(P, d.hole)
    inside = d.silhouette.buffer(-P.text_margin)
    assert inside.contains(panel)
    assert mods.within(panel.buffer(-P.qr_quiet * P.qr_module + 0.05))
    hole = Point(d.hole[0], d.hole[1]).buffer(d.hole[2] + P.hole_ring_w)
    assert panel.distance(hole) >= P.qr_gap - 1e-6
    url = B.url_polys(P, d.hole, d.silhouette)
    assert inside.contains(url) and url.distance(panel) >= P.text_gap - 0.05
    assert url.bounds[0] < -10 and url.bounds[2] > 10  # a readable width


def test_url_glyphs_print_apart_with_real_strokes(d):
    """Brown between neighbouring glyphs and the strokes themselves are at least a nozzle width."""
    url = B.url_polys(P, d.hole, d.silhouette)
    glyphs = list(url.geoms)
    nozzle = P.printer.nozzle
    for i, g in enumerate(glyphs):
        for h in glyphs[i + 1:]:
            assert g.distance(h) >= nozzle, f"glyph gap {g.distance(h):.2f}"
    assert _opened(url, nozzle).area >= 0.9 * url.area


def test_url_reads_from_the_back(d):
    """Mirrored: the first letter 'g' sits at +X in the front frame (which is the left seen from behind)."""
    url = B.url_polys(P, d.hole, d.silhouette)
    g = max(url.geoms, key=lambda p: p.bounds[2])  # rightmost glyph in the front frame
    assert len(g.interiors) == 1  # a 'g' has one counter in this font; 'm' at the other end has none
