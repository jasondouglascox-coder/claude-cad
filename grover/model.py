"""Design polygons -> one fused solid per filament. Print orientation: back face (QR) on Z=0.

Z stack:  0 .. back_t        QR panel (white) + modules (brown) inlaid; core elsewhere
          back_t .. core_top core: yellow under the ribbon, orange elsewhere
          core_top .. zone   each color patch rises to its zone's height
                             (disk < ring < tails < ribbon < Grover)
"""

from functools import lru_cache

from build123d import Color, Compound, Part
from shapely.ops import unary_union

from . import vector as V
from .design import design
from .params import P, Params

COLORS = ("orange", "yellow", "white", "brown")


def _unpinch(g, eps: float = 0.01):
    return g.buffer(eps, join_style="mitre").buffer(-eps, join_style="mitre")


def _fuse(solids: list) -> Part:
    out = solids[0] if len(solids) == 1 else solids[0].fuse(*solids[1:]).clean()
    return Part(out.solids())


@lru_cache(maxsize=2)
def bodies(p: Params = P) -> dict[str, Part]:
    d = design(p)
    panel, mods = V.qr_shapes(p)
    panel_white = panel.difference(mods)

    solids: dict[str, list] = {c: [] for c in COLORS}
    # Per color, stack one slab per layer band: footprint = every patch reaching at least that high.
    # Pinches (patches touching at a single point) are closed first, so each mesh stays manifold.
    tops = sorted({z for _, z, _ in d.pieces})
    for c in COLORS:
        mine = [(z, g) for f, z, g in d.pieces if f == c]
        lo = p.core_top
        for hi in tops:
            foot = unary_union([g for z, g in mine if z >= hi - 1e-9])
            if not foot.is_empty:
                solids[c] += V.prisms(_unpinch(foot), lo, hi)
            lo = hi
    for f, g in d.core.items():
        solids[f] += V.prisms(g.difference(panel), 0.0, p.back_t)
        solids[f] += V.prisms(g, p.back_t, p.core_top)
    solids["white"] += V.prisms(panel_white, 0.0, p.back_t)
    solids["brown"] += V.prisms(mods, 0.0, p.back_t)

    out = {}
    for c in COLORS:
        body = _fuse(solids[c])
        body.label = f"grover_{c}"
        body.color = Color(*getattr(p, c))
        out[c] = body
    return out


def assembly(p: Params = P) -> Compound:
    return Compound(children=list(bodies(p).values()), label="grover_keychain")
