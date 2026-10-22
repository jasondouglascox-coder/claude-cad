"""The rose, printed in one go: back flat on the bed (the wall side), petals up. Red PLA; the outer petals' curl needs
tree supports with a PETG interface (slicer settings, `write`).

Parts: a thin floor tying every petal's foot together, a solid cone under the centre holding the keyhole, the 24
outer petals and the 8 centre petals. The keyhole's slot runs up (+Y in the print frame) to the flower's centre, so
the nail goes where you want the centre.
"""
from functools import lru_cache
from pathlib import Path

from build123d import Align, Cone, Cylinder, Part, Pos, SlotCenterToCenter, extrude

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate
from rose_wall import petals
from rose_wall.params import Params

NAIL_D = 3.0  # nail shank
MN = (Align.CENTER, Align.CENTER, Align.MIN)


def keyhole_end(p: Params) -> float:
    """The slot's end arc centre on +Y: the nail's shank rests against the slot's top, at the flower's centre."""
    return NAIL_D / 2 - p.key_shank_w / 2


def keyhole(p: Params) -> list:
    """Cut from below: the shank slot through a lip, the head's room above it, a 45-degree roof over that."""
    end = keyhole_end(p)
    mid = end - p.key_len / 2
    at = Pos(0, mid, 0)
    roof = p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)
    slot = lambda w: SlotCenterToCenter(p.key_len, w, rotation=90)
    return [at * Pos(0, 0, -1) * extrude(slot(p.key_shank_w), p.key_lip + 1),
            Pos(0, end - p.key_len, -1) * Cylinder(p.key_head_d / 2, p.key_lip + 1, align=MN),
            at * Pos(0, 0, p.key_lip) * extrude(slot(p.key_head_d), p.key_head_room),
            at * Pos(0, 0, p.key_lip + p.key_head_room) * extrude(slot(p.key_head_d), roof, taper=45)]


def key_top(p: Params) -> float:
    return p.key_lip + p.key_head_room + p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)


@lru_cache
def parts(p: Params) -> list[Part]:
    """Every body, in the flower's frame (centre on the axis, back at z = 0): base first, then the petals."""
    cut = keyhole(p)
    floor = Cylinder(p.foot_r + p.wall, p.floor, align=MN)
    base = Cone(p.centre_r + p.base_t, p.centre_r, p.base_t, align=MN)  # flares at 45 degrees: nothing over air
    base = Part((Part((floor + base).solids()) - cut).solids())
    centre = [Part((petals.centre(p, k) - cut).solids()) for k in range(p.centre_petals)]
    outer = [petals.outer(p, i) for i in range(p.petals)]
    return [base] + centre + outer


@lru_cache
def body(p: Params) -> Part:
    """Everything fused into one solid (about two minutes: 33 overlapping curved walls)."""
    base, *rest = parts(p)
    return Part((base + rest).solids())


def centre_xy(p: Params) -> tuple[float, float]:
    """Where the flower's centre (its axis) lands: the middle of the bed."""
    return p.printer.bed / 2, (p.printer.bed_y or p.printer.bed) / 2


def make(p: Params) -> Part:
    """The rose in its print position: centred on the bed."""
    rose = Pos(*centre_xy(p), 0) * body(p)
    rose.label, rose.color = "rose", p.color(p.slot_rose)
    return rose


SUPPORT = {  # Bambu project settings: tree supports under the curled petals, PETG only where they touch the rose
    "enable_support": "1",
    "support_type": "tree(auto)",
    "support_filament": "0",  # the support's body in whatever's loaded (the rose's red)
    "support_top_z_distance": "0",  # PETG doesn't bond to PLA: it can touch, and peels clean
    "support_bottom_z_distance": "0",
    "support_interface_spacing": "0",
    "support_interface_top_layers": "3",
}


def write(p: Params, out: Path) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    support = dict(SUPPORT, support_interface_filament=str(p.slot_support))
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments), overrides=support)
    write_plates([Plate("rose", 1, [("rose", make(p))])], out / "plates", out / "plates.csv",
                 lambda name: p.slot_rose, settings=settings)
