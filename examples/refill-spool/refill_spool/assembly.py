"""The spool screwed together on its axis (Z), with the refill coil and the strap paths as solids."""
from build123d import Part, Pos, Rot

from refill_spool.params import P, Params
from refill_spool.parts import barrel_half_centered, cap_centered, radial_box, ring


def placed_parts(p: Params = P) -> list[tuple[str, Part]]:
    """Barrel half as printed; the cap flipped over onto the barrel top (x stays, y and z mirror)."""
    return [("barrel_half", barrel_half_centered(p)),
            ("cap", Pos(0, 0, p.width) * Rot(180, 0, 0) * cap_centered(p))]


def coil(p: Params = P) -> Part:
    """A full refill: cardboard core inside, 1 kg of filament out to coil_d, 0.5 mm short of each flange."""
    return Pos(0, 0, p.flange_t + 0.5) * ring(p.core_d / 2, p.coil_d / 2, p.inside_w - 1)


def strap_paths(p: Params = P) -> list[Part]:
    """One loop per strap, strap_t thick and a mm narrower than the slot: under the core in the barrel slot, out
    through both flanges, along each outer face, and back over the coil inside the rim."""
    t, w, gap = p.strap_t, p.strap_w - 1, 0.05
    top = ((p.core_d / 2 - gap) ** 2 - (w / 2) ** 2) ** 0.5  # the box's corners stay inside the core
    under = (top - t, top)
    over = (p.coil_d / 2 + gap, p.coil_d / 2 + gap + t)
    z0, h = -gap - t, p.width + 2 * (gap + t)
    paths = []
    for a in p.strap_angles():
        loop = radial_box(a, *under, w, h, z0) + radial_box(a, *over, w, h, z0)
        loop += radial_box(a, under[0], over[1], w, t, z0) + radial_box(a, under[0], over[1], w, t, p.width + gap)
        paths.append(loop)
    return paths
