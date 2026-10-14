"""Bow-tie keystone that joins two panel halves at mid-bay: at the arch crown, or (deck truss) a smaller
key in the bottom-chord splice plate."""
from dataclasses import replace

from build123d import Location, Part, Pos, Rot, extrude

from hotrain.joints import butterfly
from hotrain.params import P, Params


def key_params(p: Params) -> Params:
    """Params whose key_* fields are the key for this run style."""
    if p.run_style == "deck_truss":
        return replace(p, key_len=p.dt_key_len, key_head=p.dt_key_head, key_waist=p.dt_key_waist)
    return p


def key_z(p: Params) -> float:
    """Key center below the tie underside."""
    if p.run_style == "deck_truss":
        return -p.dt_depth + p.dt_gusset_h / 2
    return -p.crown_depth / 2


def make(p: Params = P) -> Part:
    k = key_params(p)
    return extrude(Pos(k.key_len / 2, k.key_head / 2) * butterfly(k), p.panel_t)


def place(p: Params, x: float, y_c: float) -> Location:
    k = key_params(p)
    return (Pos(x, y_c, key_z(p)) * Pos(0, p.panel_t / 2, 0) * Rot(90, 0, 0)
            * Pos(-k.key_len / 2, -k.key_head / 2, 0))
