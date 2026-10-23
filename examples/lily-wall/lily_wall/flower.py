"""The lily, printed in one go: back flat on the bed (the wall side), tepals up, white fading to purple by layers.
The tepals' arches need supports: trees in whatever's loaded, interface too (a PETG interface swapped 110 times and
took 9.8 h against 4.3), with a layer's gap so they snap off; their marks are on the undersides, at the wall.

Parts: the six tepals, a solid cone for the throat's floor holding the keyhole (the nail goes where the centre
will be), six stamens and a pistil rising from it.
"""
from functools import lru_cache
from pathlib import Path

from build123d import Align, Cone, Cylinder, Pos, Rot, SlotCenterToCenter, Sphere, extrude, scale

from cadkit import bambu3mf, slicers
from cadkit.mesh import Mesh
from lily_wall import colour, tepals
from lily_wall.params import Params

NAIL_D = 3.0  # nail shank
MN = (Align.CENTER, Align.CENTER, Align.MIN)


def keyhole_end(p: Params) -> float:
    """The slot's end arc centre on +Y: the nail's shank rests against the slot's top, at the centre."""
    return NAIL_D / 2 - p.key_shank_w / 2


def key_top(p: Params) -> float:
    return p.key_lip + p.key_head_room + p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)


def keyhole(p: Params) -> list:
    """Cut from below: the shank slot through a lip, the head's room above it, a 45-degree roof over that."""
    end = keyhole_end(p)
    at = Pos(0, end - p.key_len / 2, 0)
    roof = p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)
    slot = lambda w: SlotCenterToCenter(p.key_len, w, rotation=90)
    return [at * Pos(0, 0, -1) * extrude(slot(p.key_shank_w), p.key_lip + 1),
            Pos(0, end - p.key_len, -1) * Cylinder(p.key_head_d / 2, p.key_lip + 1, align=MN),
            at * Pos(0, 0, p.key_lip) * extrude(slot(p.key_head_d), p.key_head_room),
            at * Pos(0, 0, p.key_lip + p.key_head_room) * extrude(slot(p.key_head_d), roof, taper=45)]


def centre(p: Params) -> list[Mesh]:
    """The throat's floor (a solid cone, sloping up: nothing over air) and the stamens and pistil standing in it."""
    out = [Mesh.from_shape(Cone(p.boss_r[0], p.boss_r[1], p.boss_t, align=MN))]
    for k in range(p.stamens):
        a = tepals.angle(p, k) + 180.0 / p.stamens  # out between the tepals
        stamen = Cylinder(p.stamen_d / 2, p.stamen_len, align=MN) + Pos(0, 0, p.stamen_len) * Rot(0, 70, 0) * scale(
            Sphere(1), (p.anther[0], p.anther[0], p.anther[1]))
        # feet 1 mm up, inside the boss: tilted from the bed, a foot's edge would dip under it
        out.append(Mesh.from_shape(Rot(0, 0, a) * Pos(3, 0, 1) * Rot(0, p.stamen_tilt, 0) * stamen, tol=0.05))
    pistil = Cylinder(p.pistil_d / 2, p.pistil_len, align=MN) + Pos(0, 0, p.pistil_len) * Sphere(p.stigma_r)
    out.append(Mesh.from_shape(pistil, tol=0.05))
    return out


@lru_cache
def body(p: Params) -> Mesh:
    """Everything unioned, the keyhole cut from below."""
    whole = Mesh.union([tepals.placed(p, k) for k in range(p.tepals)] + centre(p), label="lily")
    for c in keyhole(p):
        whole = whole - c
    return whole.drop_crumbs(1.0)


@lru_cache
def coloured(p: Params) -> list[tuple[Mesh, int]]:
    """[(white body, slot), (purple body, slot)] in the flower's frame."""
    white, purple = colour.split(p, body(p))
    white.label, white.color = "lily_white", p.color(p.slot_white)
    purple.label, purple.color = "lily_purple", p.color(p.slot_purple)
    return [(white, p.slot_white), (purple, p.slot_purple)]


def centre_xy(p: Params) -> tuple[float, float]:
    return p.printer.bed / 2, (p.printer.bed_y or p.printer.bed) / 2


def make(p: Params) -> Mesh:
    """The lily in its print position: centred on the bed."""
    return body(p).translate((*centre_xy(p), 0))


SUPPORT = {  # Bambu project settings: tree supports under the arches, all in whatever's loaded (no swaps of their own)
    "enable_support": "1",
    "support_type": "tree(auto)",
    "support_filament": "0",
    "support_interface_filament": "0",
    "support_remove_small_overhang": "0",  # keep support under the finest tips
    "support_interface_spacing": "0",
    "support_interface_top_layers": "3",
}


def tower(p: Params) -> tuple[float, float, float]:
    """Prime tower (x, y, width) in the bed's front-left corner, clear of the lily."""
    return (4.0, 4.0, 35.0)


def write(p: Params, out: Path) -> None:
    """out/plates/lily.3mf: one object, its white and purple bodies as parts; lily.stl; plates.csv."""
    out = Path(out)
    (out / "plates").mkdir(parents=True, exist_ok=True)
    gap = str(p.printer.layer)  # PLA on PLA bonds: a layer's gap above and below, so the trees snap off
    support = dict(SUPPORT, support_top_z_distance=gap, support_bottom_z_distance=gap)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments), tower=tower(p),
                                       overrides=support)
    at = (*centre_xy(p), 0)
    parts = [(b.label, b.translate(at), slot) for b, slot in coloured(p)]
    s = slicers.active()
    s.write_project(out / "plates" / f"lily{s.project_suffix}", [("lily", parts)], settings)
    make(p).write_stl(out / "plates" / "lily.stl")
    (out / "plates.csv").write_text(f"plate,quantity,contents\nlily,1,lily x1 ({colour.changes(p)} colour changes)\n")
