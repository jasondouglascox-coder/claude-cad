"""Every cat cuts cleanly from vinyl, the sheet fits the mat, and the DXFs read back at the right size."""
import ezdxf
import pytest
from shapely.geometry import Polygon

from cat_decals import cats, dxf, sheet
from cat_decals.params import MM, P

NAMES = list(cats.POSES)


def test_a_dozen_poses():
    assert len(NAMES) >= 12


@pytest.mark.parametrize("name", NAMES)
def test_one_solid_piece(name):
    c = cats.cat(name)
    assert isinstance(c, Polygon) and c.is_valid and not c.is_empty


@pytest.mark.parametrize("name", NAMES)
def test_sized(name):
    x0, y0, x1, y1 = cats.cat(name).bounds
    assert (x0, y0) == pytest.approx((0, 0), abs=1e-9)
    assert max(x1 - x0, y1 - y0) == pytest.approx(P.cat_size)


@pytest.mark.parametrize("name", NAMES)
def test_nothing_too_thin_to_weed(name):
    """Opening by min_feature/2 shaves only the corners: no leg, tail or ear thinner than min_feature."""
    c = cats.cat(name)
    r = P.min_feature / 2
    lost = c.difference(c.buffer(-r).buffer(r))
    worst = max((g.area for g in getattr(lost, "geoms", [lost])), default=0)
    assert worst < P.min_feature ** 2 / 2, f"{name}: a part narrower than {P.min_feature} in"


@pytest.mark.parametrize("name", NAMES)
def test_holes_weedable(name):
    for ring in cats.cat(name).interiors:
        hole = Polygon(ring)
        assert hole.area >= P.min_hole_area, f"{name}: a hole of {hole.area:.3f} sq in"
        assert not hole.buffer(-P.min_gap / 2).is_empty, f"{name}: a hole narrower than {P.min_gap} in"


def test_sheet_fits_the_mat_with_room_to_weed():
    shapes = [s for _, s in sheet.layout()]
    x0, y0 = P.margin, P.margin
    x1, y1 = P.mat[0] - P.margin, P.mat[1] - P.margin
    for s in shapes:
        bx0, by0, bx1, by1 = s.bounds
        assert bx0 >= x0 - 1e-9 and by0 >= y0 - 1e-9 and bx1 <= x1 + 1e-9 and by1 <= y1 + 1e-9
    for i, a in enumerate(shapes):
        for b in shapes[i + 1:]:
            assert a.distance(b) >= P.spacing - 1e-9


def test_sheet_has_every_pose_and_the_test_square():
    names = [n for n, _ in sheet.layout()]
    assert set(NAMES) <= set(names)
    assert names.count("test_square") == 1
    assert len(names) >= 3 * len(NAMES)  # lots of little cats


@pytest.mark.parametrize("units, scale", [("in", 1.0), ("mm", MM)])
def test_dxf_reads_back_closed_and_to_scale(tmp_path, units, scale):
    shapes = sheet.layout()
    path = tmp_path / f"sheet_{units}.dxf"
    dxf.write(path, [s for _, s in shapes], units)
    doc = ezdxf.readfile(path)
    lines = list(doc.modelspace())
    assert lines and all(e.dxftype() == "POLYLINE" and e.is_closed for e in lines)
    rings = sum(1 + len(s.interiors) for _, s in shapes)
    assert len(lines) == rings  # every outline and hole is its own closed cut
    xs = [v.dxf.location.x for e in lines for v in e.vertices]
    ys = [v.dxf.location.y for e in lines for v in e.vertices]
    assert max(xs) <= P.mat[0] * scale and max(ys) <= P.mat[1] * scale and min(xs) >= 0 and min(ys) >= 0
    square = dict(shapes)["test_square"]
    x0, y0, x1, y1 = square.bounds
    assert (x1 - x0, y1 - y0) == pytest.approx((P.test_square, P.test_square))
