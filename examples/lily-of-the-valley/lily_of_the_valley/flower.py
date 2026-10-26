"""The lily of the valley, printed in one go: back flat on the bed (the wall side), green PLA up to the seam and
white above it, one swap. No supports: every part is a tube whose underside runs in to the bed at 45 degrees or
steeper, hidden under its round top. It hangs on a nail through a keyhole under the bell over its centre of mass.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from build123d import Align, Box, Cylinder, Pos, SlotCenterToCenter, extrude

from cadkit import bambu3mf, slicers
from cadkit.mesh import Mesh
from lily_of_the_valley import bell, sprig
from lily_of_the_valley.params import Params

NAIL_D = 3.0  # nail shank
MN = (Align.CENTER, Align.CENTER, Align.MIN)
BIG = 600.0
ROOF = 44.0  # the keyhole roof's lean from upright: just under 45, so float error never tips it over


@lru_cache
def unkeyed(p: Params) -> Mesh:
    return Mesh.union(sprig.parts(p), "sprig")


def hang_point(p: Params) -> tuple[float, float]:
    """Where the nail's centre sits: key_at down the key bell's axis from its apex, moved sideways (within the
    bell) to straight above the centre of mass, so the sprig hangs plumb."""
    apex, axis, size = sprig.frame(p, p.key_bell)
    x, y = apex + axis * p.key_at
    t = p.key_at / (p.bell_len * p.bell_r * size)
    room = p.bell_r * size * float(bell.profile(t, p)) - p.key_head_d / 2 - p.key_wall - 1.0
    cx = unkeyed(p).centroid[0]
    return float(np.clip(cx, x - room, x + room)), float(y)


def key_top(p: Params) -> float:
    return p.key_lip + p.key_head_room + p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)


def keyhole(p: Params, grow: float = 0.0) -> list:
    """Cut from below, the slot running down from the hang point: the shank slot through a lip, the head's room
    above it, a 44-degree roof over that. grow: the same, bigger by that all round (the wall it needs)."""
    hx, hy = hang_point(p)
    end = hy + NAIL_D / 2 - p.key_shank_w / 2  # the slot's top arc centre: the nail rests against it
    at = Pos(hx, end - p.key_len / 2, 0)
    roof = p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)
    slot = lambda w: SlotCenterToCenter(p.key_len, w, rotation=90)
    head = p.key_head_d + 2 * grow
    if grow:
        return [at * Pos(0, 0, -1) * extrude(slot(head), p.key_lip + p.key_head_room + 1),
                at * Pos(0, 0, p.key_lip + p.key_head_room) * extrude(slot(head), roof + grow, taper=ROOF)]
    return [at * Pos(0, 0, -1) * extrude(slot(p.key_shank_w), p.key_lip + 1),
            Pos(hx, end - p.key_len, -1) * Cylinder(p.key_head_d / 2, p.key_lip + 1, align=MN),
            at * Pos(0, 0, p.key_lip) * extrude(slot(p.key_head_d), p.key_head_room),
            at * Pos(0, 0, p.key_lip + p.key_head_room) * extrude(slot(p.key_head_d), roof, taper=ROOF)]


def probe_up(p: Params):
    """A thin bar up the keyhole's centre line at the lip: it crosses the slot's top where the nail rests."""
    hx, hy = hang_point(p)
    return Pos(hx - 0.05, hy - p.key_len - p.key_head_d, p.key_lip / 2) * Box(
        0.1, p.key_len + p.key_head_d + 20, 0.1, align=(Align.MIN, Align.MIN, Align.MIN))


@lru_cache
def body(p: Params) -> Mesh:
    whole = unkeyed(p)
    for c in keyhole(p):
        whole = whole - c
    return whole.drop_crumbs(1.0).simplify()  # the union's slivers (where bells nearly meet) collapsed


@lru_cache
def coloured(p: Params) -> list[tuple[Mesh, int]]:
    """[(green body, slot), (white body, slot)]: the sprig cut at the seam, green below, white above."""
    above = Mesh.from_shape(Pos(0, 0, p.seam) * Box(BIG, BIG, BIG, align=MN))
    b = body(p)
    green, white = b - above, b & above
    green.label, green.color = "sprig_green", p.color(p.slot_green)
    white.label, white.color = "sprig_white", p.color(p.slot_white)
    return [(green, p.slot_green), (white, p.slot_white)]


def centre_xy(p: Params) -> tuple[float, float]:
    return p.printer.bed / 2, (p.printer.bed_y or p.printer.bed) / 2


def make(p: Params) -> Mesh:
    """The sprig in its print position: centred on the bed."""
    return body(p).translate((*centre_xy(p), 0))


def tower(p: Params) -> tuple[float, float, float]:
    """Prime tower (x, y, width) in the bed's front-right corner, clear of the sprig (it leans left at the foot)."""
    return (p.printer.bed - 4.0 - 35.0, 4.0, 35.0)


def write(p: Params, out: Path) -> None:
    """out/plates/lily_of_the_valley.3mf: one object, its green and white bodies as parts; the STL; plates.csv."""
    out = Path(out)
    (out / "plates").mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments), tower=tower(p))
    at = (*centre_xy(p), 0)
    parts = [(b.label, b.translate(at), slot) for b, slot in coloured(p)]
    s = slicers.active()
    s.write_project(out / "plates" / f"lily_of_the_valley{s.project_suffix}", [("lily_of_the_valley", parts)],
                    settings)
    make(p).write_stl(out / "plates" / "lily_of_the_valley.stl")
    (out / "plates.csv").write_text("plate,quantity,contents\nlily_of_the_valley,1,sprig x1 (1 colour change)\n")
