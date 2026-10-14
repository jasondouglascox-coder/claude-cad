"""2D regions -> one body per filament, in PRINT orientation: back on Z = 0, front relief up.

    0 .. z_back       back inlay: white QR panel (modules = brown body) and white URL, brown elsewhere
    z_back .. z_body  solid brown
    z_body .. z_base  base band: white under disc / cat / ribbon, orange ring
    z_base .. z_face  face band: yellow ribbon, white cat + orange patches, brown ink; ring ink to z_ring_ink
    z_face .. z_top   top band: white paws + glints, brown eyes, nose, letters, paw lines
Every body may be several solids (brown ink columns stand on white and orange); the fused keychain is one."""
from functools import lru_cache

from build123d import Align, Color, Compound, Cone, Cylinder, Part, Pos, extrude
from shapely.geometry import Point

from . import back as B
from . import vec as V
from .params import P, Params
from .regions import band_regions, design

COLORS = ("orange", "yellow", "white", "brown")


def _fuse(solids: list) -> Part:
    if not solids:
        raise ValueError("nothing to fuse")
    out = solids[0] if len(solids) == 1 else solids[0].fuse(*solids[1:]).clean()
    return Part(out.solids())


def hole_cutter(p: Params, hole: tuple) -> Part:
    hx, hy, hr = hole
    c = p.hole_chamfer
    mn = (Align.CENTER, Align.CENTER, Align.MIN)
    cut = Pos(hx, hy, -1) * Cylinder(hr, p.thickness + 2, align=mn)
    cut += Pos(hx, hy, p.z_ring_ink - c) * Cone(hr, hr + c + 0.05, c + 0.05, align=mn)  # the hole ring's top
    cut += Pos(hx, hy, -0.05) * Cone(hr + c + 0.05, hr, c + 0.05, align=mn)
    return Part(cut.solids())


@lru_cache(maxsize=2)
def bodies(p: Params = P) -> dict[str, Part]:
    d = design(p)
    panel, mods = B.qr_shapes(p, d.hole)
    url = B.url_sketch(p, d.hole, d.silhouette)
    solids = {c: [] for c in COLORS}

    # back inlay and body
    pockets = panel  # the URL pocket is cut with build123d below
    solids["white"] += V.prisms(panel.difference(mods), 0, p.z_back)
    body = _fuse(V.prisms(d.silhouette.difference(pockets), 0, p.z_back) + V.prisms(d.silhouette, p.z_back, p.z_body))
    url_solid = Part(extrude(url, p.z_back).solids())
    body = Part((body - url_solid).solids())
    solids["brown"].append(body)
    solids["white"].append(url_solid)

    # front bands
    for color, lo, hi, g in band_regions(d):
        if not g.is_empty:
            solids[color] += V.prisms(g, getattr(p, lo), getattr(p, hi))

    cutter = hole_cutter(p, d.hole)
    out = {}
    for c in COLORS:
        part = _fuse(solids[c])
        if (part & cutter).volume > 1e-6:
            part = Part((part - cutter).solids())
        part.label = f"grover_{c}"
        part.color = Color(*p.colors[c])
        out[c] = part
    return out


def keychain(p: Params = P) -> Compound:
    """All four bodies, labeled and colored, as one print part."""
    return Compound(children=list(bodies(p).values()), label="grover_keychain")


def fused(p: Params = P) -> Part:
    """Every color fused: must be one solid."""
    return _fuse(list(bodies(p).values()))
