"""2D regions -> one body per filament, in PRINT orientation: back on Z = 0, front relief up.

    0 .. z_back       back inlay: white QR panel (modules = brown body) and white URL, brown elsewhere
    z_back .. z_body  solid brown
    z_body .. z_base  base band: white under disc / cat / ribbon, orange ring
    z_base .. z_face  face band: yellow ribbon, white cat + orange patches, brown ink; ring ink to z_ring_ink
    z_face .. z_top   top band: white paws, eye crescents + glints, brown eyes, nose, letters, paw lines
Every body may be several solids (brown ink columns stand on white and orange); the bands' footprints
stacked are one solid."""
from functools import lru_cache

from build123d import Align, Color, Compound, Cone, Cylinder, Part, Pos, extrude
from shapely.geometry import Point
from shapely.ops import unary_union

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
    pockets = panel.difference(mods)  # only the white is a pocket: the dark modules are brown body
    solids["white"] += V.prisms(pockets, 0, p.z_back)
    body = _fuse(V.prisms(d.silhouette.difference(pockets), 0, p.z_back) + V.prisms(d.silhouette, p.z_back, p.z_body))
    url_solid = Part(extrude(url, p.z_back).solids())
    body = Part((body - url_solid).solids())
    solids["brown"].append(body)
    solids["white"].append(url_solid)

    # front bands. The ring ink runs 0.05 mm on under the face band's brown it meets: same color, and the solids
    # then join by overlapping instead of along a knife edge
    for color, lo, hi, g in band_regions(d):
        if g is d.ring_ink:
            g = unary_union([g, g.buffer(0.05).intersection(d.face_ink)])
            g = g.buffer(0.003, join_style="mitre").buffer(-0.003, join_style="mitre")  # weld point contacts
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


@lru_cache(maxsize=2)
def fused(p: Params = P) -> Part:
    """The whole keychain as one shape: each band's footprint (all its colors) extruded and stacked, with the hole
    cut. Must be one solid. (Fusing the four color bodies themselves, which share thousands of faces exactly, is
    more than OCC does reliably; each body is checked on its own.)"""
    d = design(p)
    bands = {}
    for _, lo, hi, g in band_regions(d):
        bands.setdefault((lo, hi), []).append(g)
    solids = V.prisms(d.silhouette, 0, p.z_body)
    for (lo, hi), gs in bands.items():
        solids += V.prisms(unary_union(gs), getattr(p, lo), getattr(p, hi))
    return Part((_fuse(solids) - hole_cutter(p, d.hole)).solids())
