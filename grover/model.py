"""Traced logo -> one solid per filament. Print orientation: back face (QR) on Z=0.

Z stack:  0 .. back_t        QR panel (white) + modules (brown) inlaid; core elsewhere
          back_t .. core_top core: yellow under the ribbon, orange elsewhere
          core_top .. zone   each color patch rises to its zone's height
                             (disk < ring < tails < cat < banner < paws)
"""

from functools import lru_cache

from build123d import Color, Compound, Part

from . import vector as V
from .params import P, Params
from .trace import maps

COLORS = ("orange", "yellow", "white", "brown")


def _fuse(solids: list) -> Part:
    if len(solids) == 1:
        out = solids[0]
    else:
        out = solids[0].fuse(*solids[1:]).clean()
    return Part(out.solids())


@lru_cache(maxsize=2)
def bodies(p: Params = P) -> dict[str, Part]:
    m = maps(p)
    lay = V.layout(m, p)
    panel, mods = V.qr_shapes(p)
    panel_white = panel.difference(mods)

    solids: dict[str, list] = {c: [] for c in COLORS}
    for f, z, g in lay["top"]:
        solids[f] += V.prisms(g, p.core_top, z)
    for f, g in lay["core"].items():
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
