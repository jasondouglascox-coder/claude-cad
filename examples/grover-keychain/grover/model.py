"""2D regions -> one body per filament, in PRINT orientation: back on Z = 0, front relief up.

    0 .. z_back       back inlay: white QR panel (modules = brown body) and white URL, brown elsewhere
    z_back .. z_body  solid brown
    z_body .. z_base  base band: white under disc / cat / ribbon, orange ring
    z_base .. z_face  face band: yellow ribbon, white cat + orange patches, brown ink and ring ink
    z_face .. z_top   top band: white paws, eye crescents + glints, brown eyes, nose, letters, paw lines
The ribbon's folds and tails are sunk below the banner (params fold_sink, tail_sink): their bands move down, the
base under them is one white layer and the body gives up the rest. Every body may be several solids (brown ink
columns stand on white and orange); the bands' footprints stacked are one solid."""
from functools import lru_cache

import shapely
from build123d import Align, Color, Compound, Cone, Cylinder, Part, Pos, extrude
from shapely.geometry import Point
from shapely.ops import unary_union

from . import back as B
from . import vec as V
from .params import P, Params
from .regions import band_regions, design

COLORS = ("orange", "yellow", "white", "brown")
FUZZ = 1e-4  # mm: what cadkit.checks.open_edges merges mesh vertices by


def _fuse(solids: list, tol: float | None = None) -> Part:
    """One shape of solids; with tol, a fuzzy fuse: faces closer than tol are one (slabs cut from different sources
    leave walls a fraction of a micron apart, which the mesh would fold into one edge)."""
    if not solids:
        raise ValueError("nothing to fuse")
    out = solids[0] if len(solids) == 1 else solids[0].fuse(*solids[1:], tol=tol).clean()
    return Part(out.solids())


def hole_cutter(p: Params, hole: tuple) -> Part:
    hx, hy, hr = hole
    c = p.hole_chamfer
    mn = (Align.CENTER, Align.CENTER, Align.MIN)
    cut = Pos(hx, hy, -1) * Cylinder(hr, p.thickness + 2, align=mn)
    cut += Pos(hx, hy, p.z_ring_ink - c) * Cone(hr, hr + c + 0.05, c + 0.05, align=mn)  # the hole ring's top
    cut += Pos(hx, hy, -0.05) * Cone(hr + c + 0.05, hr, c + 0.05, align=mn)
    return Part(cut.solids())


def sunk_z(p: Params, name: str, s: int) -> float:
    """A band boundary's height under a ribbon piece sunk s layers: the bands from the base's top up move down s;
    the base keeps at least one layer (white under the yellow) and the body gives up the rest."""
    layers = {"z_body": p.body_layers, "z_base": p.body_layers + p.base_layers}
    layers |= {"z_ring_ink": layers["z_base"] + p.ring_ink_layers, "z_face": layers["z_base"] + p.face_layers}
    layers["z_top"] = layers["z_face"] + p.top_layers
    return p.z(layers[name] - (max(s - (p.base_layers - 1), 0) if name == "z_body" else s))


def sinks(d) -> list:
    """[(footprint, layers)]: each sunk ribbon piece, grown to take whole any yellow fill it holds, so the fill's
    own edge is the step and no fill is cut into a sliver."""
    out = []
    for g, s in d.sinks:
        if s and not g.is_empty:
            fills = [q for q in d.ribbon.geoms if g.contains(q.representative_point())]
            out.append((V.multi(unary_union([g, *fills])), s))
    return out


def stack(p: Params, d) -> list:
    """[(color, z0, z1, region, raised)]: the body and band_regions, with the sunk ribbon pieces moved down. Under
    a sunk piece the base is white, brown under its lines (they stand on the body); round it the base under any
    brown line is brown too, so a line on either side of a step stands on brown, and slivers a cut leaves along a
    line join the brown beside them."""
    bands = [("brown", "z_back", "z_body", d.silhouette)] + band_regions(d)
    sunk_pieces = sinks(d)
    if not sunk_pieces:
        return [(c, getattr(p, lo), getattr(p, hi), g, lo == "z_face") for c, lo, hi, g in bands]
    sunk = unary_union([g for g, _ in sunk_pieces])
    ink = unary_union([d.face_ink, d.ring_ink])
    beside = V.multi(ink.intersection(sunk.buffer(2 * p.line_w)).difference(sunk))
    out = [("brown", p.z_body, p.z_base, beside, False)]
    for c, lo, hi, g in bands:
        rest = g.difference(sunk)
        out.append((c, getattr(p, lo), getattr(p, hi), rest.difference(beside) if lo == "z_body" else rest,
                    lo == "z_face"))
    for g, s in sunk_pieces:
        z = {n: sunk_z(p, n, s) for n in ("z_body", "z_base", "z_ring_ink", "z_face", "z_top")}
        z["z_back"] = p.z_back
        out += [(c, z[lo], z[hi], r.intersection(g), lo == "z_face") for c, lo, hi, r in bands if lo != "z_body"]
        lines = ink.intersection(g)
        out += [("brown", z["z_body"], z["z_base"], lines, False),
                ("white", z["z_body"], z["z_base"], g.difference(lines), False)]
    out = [(c, z0, z1, V.multi(g), raised) for c, z0, z1, g, raised in out if z1 > z0]
    return [b for b in out if not b[3].is_empty]


def slabs(items: list, weld: float = 0.003, jog: float = 1e-4) -> list:
    """[(z0, z1, region)]: (z0, z1, region) items cut at every height any of them starts or ends and unioned
    within each slab, the slabs a run of the same items covers merged. Pieces of one shape at different heights
    then only ever meet on a horizontal face: none share a wall OCC would have to fuse. Each slab is rid of spikes
    narrower than 2 * weld (where edges cut from different sources a few nanometres apart were unioned: never a
    ledge too thin to mesh), then welded (parts touching at a point join, and notches as narrow close), and a
    vertex closer than jog to the one before it goes (the mesh would merge the two: cadkit.checks.open_edges)."""
    zs = sorted({z for z0, z1, _ in items for z in (z0, z1)})
    out, last = [], None
    for a, b in zip(zs, zs[1:]):
        key = frozenset(i for i, (z0, z1, _) in enumerate(items) if z0 <= a and z1 >= b)
        if not key:
            last = None
            continue
        if key == last:
            out[-1] = (out[-1][0], b, out[-1][2])
            continue
        g = unary_union([items[i][2] for i in key])
        for e in (-weld, weld, weld, -weld):
            g = g.buffer(e, join_style="mitre")
        out.append((a, b, V.multi(shapely.remove_repeated_points(g, jog).buffer(0))))
        last = key
    return out


@lru_cache(maxsize=2)
def bodies(p: Params = P) -> dict[str, Part]:
    d = design(p)
    panel, mods = B.qr_shapes(p, d.hole)
    url = B.url_sketch(p, d.hole, d.silhouette)
    solids = {c: [] for c in COLORS}

    # back inlay, body and front bands, a color at a time in slabs (regions of one color at the same height are one
    # shape, welded where parts touch at a point); the raised top band stands 0.01 mm in from its edges, so it
    # never sits flush on the face band's same color below. Either way two solids of one color would otherwise
    # share faces edge to edge, and the fused mesh gets T-junctions (open edges).
    pockets = panel.difference(mods)  # only the white is a pocket: the dark modules are brown body
    items = {c: [] for c in COLORS}
    items["white"].append((0.0, p.z_back, pockets))
    items["brown"].append((0.0, p.z_back, d.silhouette.difference(pockets)))
    for color, z0, z1, g, raised in stack(p, d):
        items[color].append((z0, z1, g.buffer(-0.01, join_style="mitre") if raised else g))
    for color, its in items.items():
        for z0, z1, g in slabs(its):
            if not g.is_empty:
                solids[color] += V.prisms(g, z0, z1)
    url_solid = Part(extrude(url, p.z_back).solids())
    solids["brown"] = [Part((_fuse(solids["brown"], FUZZ) - url_solid).solids())]
    solids["white"].append(url_solid)

    cutter = hole_cutter(p, d.hole)
    out = {}
    for c in COLORS:
        part = _fuse(solids[c], FUZZ)
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
    """The whole keychain as one shape: every color's regions stacked in slabs and extruded, with the hole cut.
    Must be one solid. (Fusing the four color bodies themselves, which share thousands of faces exactly, is more
    than OCC does reliably; each body is checked on its own.)"""
    d = design(p)
    items = [(0.0, p.z_back, d.silhouette)] + [(z0, z1, g) for _, z0, z1, g, _ in stack(p, d)]
    solids = [pr for z0, z1, g in slabs(items) for pr in V.prisms(g, z0, z1)]
    return Part((_fuse(solids) - hole_cutter(p, d.hole)).solids())
