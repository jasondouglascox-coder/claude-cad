"""The rose, printed in one go: back flat on the bed (the wall side), petals up. Red PLA; the outer petals' curl needs
tree supports with a PETG interface (slicer settings, `write`).

Parts: a thin floor under each petal tying their feet together (never showing past them), a solid cone under the centre holding the keyhole, the 24
outer petals and the 8 centre petals (the small rose: 4, round a nub). The keyhole's slot runs up (+Y in the print frame) to the flower's centre, so
the nail goes where you want the centre.
"""
from functools import lru_cache
from pathlib import Path

from build123d import Align, Box, Cone, Cylinder, Part, Pos, SlotCenterToCenter, extrude

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


def pocket(p: Params) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) of the keyhole's footprint, from the flower's centre: the nail head's pocket and slot."""
    end, r = keyhole_end(p), p.key_head_d / 2
    return (-r, end - p.key_len - r, r, end + r)


def blocker(p: Params) -> Part:
    """No support in the keyhole: a box over its whole footprint from the bed to just over its roof. It has to take
    in the whole roof (Bambu grows support back from any strip of overhang left outside it); a flat roof otherwise
    gets tree support up through the head hole, filling the pocket and trapped behind the lip."""
    x0, y0, x1, y1 = pocket(p)
    m = 1.0  # past the pocket's sides
    return Pos(x0 - m, y0 - m, 0) * Box(x1 - x0 + 2 * m, y1 - y0 + 2 * m, key_top(p) + 2 * p.printer.layer,
                                        align=(Align.MIN, Align.MIN, Align.MIN))


def nub_top(p: Params) -> float:
    """The nub's top, on a layer, `nub[2]` under the innermost centre petal's rim."""
    return p.printer.snap(petals.centre_line(p, 0)[-1][1] - p.nub[2])


def nub(p: Params) -> Part | None:
    """A cone plugging the very middle, inside the innermost centre petal (None when the rose has none)."""
    return Cone(p.nub[0], p.nub[1], nub_top(p), align=MN) if p.nub else None


@lru_cache
def parts(p: Params) -> list[Part]:
    """Every body, in the flower's frame (centre on the axis, back at z = 0): base first, then the petals."""
    cut = keyhole(p)
    floor = [petals.pad(p, i) for i in range(p.petals)]  # under each petal only: no lip past the feet
    base = Cone(p.centre_r + p.base_t, p.centre_r, p.base_t, align=MN)  # flares at 45 degrees: nothing over air
    base = Part((Part((base + floor).solids()) - cut).solids())
    centre = [Part((petals.centre(p, k) - cut).solids()) for k in range(p.centre_petals)]
    if p.nub:
        centre.insert(0, Part((nub(p) - cut).solids()))
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
    "support_remove_small_overhang": "0",  # else the slicer drops the support under the smallest curl tips
    "support_interface_spacing": "0",
    "support_interface_top_layers": "3",
}


TOWER_W = 35.0


def spots(p: Params) -> list[tuple[float, float]]:
    """Where each rose's centre goes on the plate: one in the middle, or four in a square `pitch` apart."""
    cx, cy = centre_xy(p)
    if p.per_plate == 1:
        return [(cx, cy)]
    assert p.per_plate == 4, "one rose a plate, or four"
    d = p.pitch / 2
    return [(cx - d, cy - d), (cx + d, cy - d), (cx - d, cy + d), (cx + d, cy + d)]


def tower(p: Params) -> tuple[float, float, float]:
    """Prime tower (x, y, width): in the bed's front-left corner, well clear of one round rose (the template's spot
    clears it by only a few mm); in the middle of four, where they leave the most room."""
    if p.per_plate == 1:
        return (4.0, 4.0, TOWER_W)
    cx, cy = centre_xy(p)
    return (cx - TOWER_W / 2, cy - TOWER_W / 2, TOWER_W)


def write(p: Params, out: Path) -> None:
    """out/plates/<p.name>.3mf (+ .step), its settings and its plates CSV, named after the plate."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # tree trunks standing on the floor between petals get no PETG under them: a layer's gap lets them break free
    support = dict(SUPPORT, support_interface_filament=str(p.slot_support),
                   support_bottom_z_distance=str(p.printer.layer))
    settings = bambu3mf.write_settings(out / f"{p.name}_settings.config", list(p.filaments), tower=tower(p),
                                       overrides=support)
    one, block = body(p), blocker(p)
    roses, blockers = [], []
    for k, (x, y) in enumerate(spots(p)):
        rose = Pos(x, y, 0) * one
        rose.color = p.color(p.slot_rose)
        name = "rose" if p.per_plate == 1 else f"rose#{k + 1}"
        roses.append((name, rose))
        blockers.append((name, Pos(x, y, 0) * block))
    write_plates([Plate(p.name, 1, roses, blockers=blockers)], out / "plates", out / f"{p.name}.csv",
                 lambda name: p.slot_rose, settings=settings)
