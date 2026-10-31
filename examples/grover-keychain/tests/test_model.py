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
    assert bb.size.X == pytest.approx(P.width - 2 * P.ribbon_slide, abs=0.6)  # the logo's width, tails slid in


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


def sunk_layers(s: int):
    """(white layers, yellow and brown layers) under a ribbon piece sunk s layers below the banner: its face band
    moved down s, on at least one layer of white (the base band, the body cut for the rest)."""
    face_top = P.body_layers + P.base_layers + P.face_layers
    yellow = range(face_top - s - P.face_layers + 1, face_top - s + 1)
    return range(yellow[0] - max(P.base_layers - s, 1), yellow[0]), yellow


def expected_colors():
    """{layer: colors}: 2 on the back, 1 in the body, 2 in the base, 4 in the face, 2 on top, and the sunk folds and
    tails add their white, yellow and brown to the layers they sank into."""
    expect = {}
    for k in range(1, int(round(P.thickness / P.printer.layer)) + 1):
        z = P.z(k) - P.printer.layer / 2
        if z < P.z_back:
            expect[k] = {"brown", "white"}
        elif z < P.z_body:
            expect[k] = {"brown"}
        elif z < P.z_base:
            expect[k] = {"white", "orange"}
        elif z < P.z_face:
            expect[k] = {"white", "orange", "yellow", "brown"}
        else:
            expect[k] = {"white", "brown"}
    for s in (P.fold_sink, P.tail_sink):
        white, yellow = sunk_layers(s)
        for k in white:
            expect[k] |= {"white"}
        for k in yellow:
            expect[k] |= {"yellow", "brown"}
    return expect


def test_colors_per_layer_follow_the_stack(b):
    expect = expected_colors()
    for k, want in expect.items():
        assert _colors_at(b, P.z(k) - P.printer.layer / 2) == want, f"layer {k}"
    assert sum(len(v) - 1 for v in expect.values()) == P.color_changes  # the accepted budget


def _column(b, x, y):
    """{color: (z min, z max)} of each body in a thin stick at (x, y)."""
    stick = Pos(x - 0.05, y - 0.05, -1) * Box(0.1, 0.1, P.thickness + 2, align=(Align.MIN,) * 3)
    out = {}
    for c, part in b.items():
        hit = part & stick
        if hit.volume > 1e-6:
            bb = hit.bounding_box()
            out[c] = (round(bb.min.Z, 3), round(bb.max.Z, 3))
    return out


def test_folds_and_tails_sink_below_the_banner(b):
    from grover import vec as V
    from grover.regions import design
    d = design(P)
    assert sorted(s for _, s in d.sinks) == [P.fold_sink] * 2 + [P.tail_sink] * 2
    for footprint, s in d.sinks:
        white, yellow = sunk_layers(s)
        fill = max(V.multi(d.ribbon.intersection(footprint.buffer(-0.3))).geoms, key=lambda g: g.area)
        x, y = fill.representative_point().coords[0]
        col = _column(b, x, y)
        assert col["yellow"] == (P.z(yellow[0] - 1), P.z(yellow[-1])), s
        assert col["white"][1] == P.z(white[-1]) and col["white"][0] <= P.z(white[0] - 1), s
        assert max(hi for _, hi in col.values()) == P.z(yellow[-1]), s  # nothing over it: open to the sky


def test_every_band_rests_on_the_one_below(b):
    everything = Compound(children=list(b.values()))
    for z in (P.z_back, P.z_body, P.z_base, P.z_face):
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


def _section_polys(body, z):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    polys = []
    for f in section(body, Plane.XY.offset(z)).faces():
        v, tris = f.tessellate(0.02, 0.2)
        pts = [(q.X, q.Y) for q in v]
        polys.append(unary_union([Polygon([pts[i], pts[j], pts[k]]) for i, j, k in tris]))
    return unary_union(polys)


def _back_image(b, px_per_mm=12):
    """Raster of the bed face from the solids themselves: what each body puts on the plate."""
    import tempfile
    from pathlib import Path
    from grover.render import draw
    path = Path(tempfile.mkdtemp()) / "back.png"
    draw([("brown", _section_polys(b["brown"], 0.05)), ("white", _section_polys(b["white"], 0.05))],
         path, P, bg="#808080", px_per_mm=px_per_mm, mirror=True)
    return cv2.imread(str(path))


def test_qr_modules_are_brown_body_on_the_plate(b):
    """The dark modules are the body, not voids: brown covers panel minus white at the bed."""
    from grover import back as B
    from grover.regions import design
    panel, mods = B.qr_shapes(P, design(P).hole)
    brown = _section_polys(b["brown"], 0.05)
    assert brown.intersection(mods).area == pytest.approx(mods.area, rel=0.02)


def test_hole_ring_survives_the_chamfer(b):
    """At the top of the brown ring around the hole, after the chamfer, at least a line width is left."""
    from grover.regions import design
    x, y, r = design(P).hole
    probe = Pos(x - r - P.hole_ring_w - 1, y - 0.05, P.z_ring_ink - 0.02) * Box(2 * (r + P.hole_ring_w + 1), 0.1, 0.01,
                                                                               align=(Align.MIN,) * 3)
    pieces = sorted((s.bounding_box() for s in (b["brown"] & probe).solids()), key=lambda bb: bb.min.X)
    assert len(pieces) == 2
    for bb in pieces:
        assert bb.size.X >= P.line_w - 0.02


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
