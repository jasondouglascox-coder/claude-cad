"""The solids: printable, watertight, on layer boundaries, colors disjoint, every band supported."""
import cv2
import numpy as np
import pytest
from build123d import Align, Box, Compound, Plane, Pos, section

from cadkit.checks import off_layer_z, open_edges, printable_problems, unsupported
from grover.model import COLORS, bodies, fused
from grover.params import P


@pytest.fixture(scope="module")
def b():
    return bodies(P)


@pytest.fixture(scope="module")
def whole():
    return fused(P)


def test_each_body_valid_watertight_on_layers(b):
    assert set(b) == set(COLORS)
    for c, part in b.items():
        assert part.is_valid, c
        assert open_edges(part) == 0, c
        assert off_layer_z(part, P.printer) == [], c


def test_whole_keychain_is_one_printable_solid(whole):
    assert printable_problems(Pos(P.width, P.width, 0) * whole, P.printer) == []
    bb = whole.bounding_box()
    assert bb.min.Z == pytest.approx(0, abs=1e-6) and bb.max.Z == pytest.approx(P.thickness, abs=1e-6)
    assert bb.size.X == pytest.approx(P.width, abs=0.3)


def test_colors_never_overlap(b):
    parts = list(b.items())
    for i, (c1, p1) in enumerate(parts):
        for c2, p2 in parts[i + 1:]:
            assert (p1 & p2).volume < 0.01, f"{c1} overlaps {c2}"


def _colors_at(b, z):
    out = set()
    for c, part in b.items():
        s = section(part, Plane.XY.offset(z))
        if s is not None and s.area > 0.05:
            out.add(c)
    return out


def test_colors_per_layer_follow_the_stack(b):
    """The whole point of the stack: 2 colors on the back, 1 in the body, 2 in the base, 4 in the face, 2 on top."""
    layer = P.printer.layer
    expect = {}
    for k in range(1, int(round(P.thickness / layer)) + 1):
        z = P.z(k) - layer / 2
        if z < P.z_back:
            expect[z] = {"brown", "white"}
        elif z < P.z_body:
            expect[z] = {"brown"}
        elif z < P.z_base:
            expect[z] = {"white", "orange"}
        elif z < P.z_face:
            expect[z] = {"white", "orange", "yellow", "brown"}
        else:
            expect[z] = {"white", "brown"}
    for z, want in expect.items():
        assert _colors_at(b, z) == want, f"z={z}"
    swaps = sum(len(v) - 1 for v in expect.values())
    assert swaps == P.back_layers + P.base_layers + 3 * P.face_layers + P.top_layers


def test_every_band_rests_on_the_one_below(b):
    everything = Compound(children=list(b.values()))
    for z in (P.z_body, P.z_base, P.z_face):
        above = everything & Pos(-100, -100, z) * Box(200, 200, 0.1, align=(Align.MIN,) * 3)
        below = everything & Pos(-100, -100, z - 0.3) * Box(200, 200, 0.3, align=(Align.MIN,) * 3)
        assert unsupported(above, below) == pytest.approx(0, abs=0.05), f"z={z}"


def test_hole_goes_through_with_chamfers(whole):
    from grover.regions import design
    x, y, r = design(P).hole
    probe = Pos(x - r - 1, y - 0.05, P.thickness / 2) * Box(2 * r + 2, 0.1, 0.1, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (whole & probe).solids()), key=lambda bb: bb.min.X)
    assert len(pieces) == 2
    assert pieces[1].min.X - pieces[0].max.X == pytest.approx(P.hole_d, abs=0.03)
    top = Pos(x - r - 1, y - 0.05, P.z_ring_ink - 0.05) * Box(2 * r + 2, 0.1, 0.1, align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (whole & top).solids()), key=lambda bb: bb.min.X)
    assert pieces[1].min.X - pieces[0].max.X > P.hole_d + P.hole_chamfer  # chamfer widens the mouth


def _back_image(b, px_per_mm=12):
    """Raster of the bed face: white where the white body touches the plate, dark elsewhere."""
    from grover.render import draw
    from grover.regions import design
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polys = []
    for f in section(b["white"], Plane.XY.offset(0.05)).faces():
        v, tris = f.tessellate(0.02, 0.2)
        pts = [(q.X, q.Y) for q in v]
        polys.append(unary_union([Polygon([pts[i], pts[j], pts[k]]) for i, j, k in tris]))
    white = unary_union(polys)
    import tempfile
    from pathlib import Path
    path = Path(tempfile.mkdtemp()) / "back.png"
    draw([("brown", design(P).silhouette), ("white", white)], path, P, bg="#808080", px_per_mm=px_per_mm, mirror=True)
    return cv2.imread(str(path))


def test_qr_decodes_from_the_bed_face(b):
    img = _back_image(b)
    det = cv2.QRCodeDetector()
    text, pts, _ = det.detectAndDecode(img)
    assert text == P.qr_text
    # first-layer squish: the brown modules grow ~0.1 mm; the code must survive it
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = max(1, int(round(0.1 * 12)))
    squished = cv2.erode(gray, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
    text2, _, _ = det.detectAndDecode(squished)
    assert text2 == P.qr_text
