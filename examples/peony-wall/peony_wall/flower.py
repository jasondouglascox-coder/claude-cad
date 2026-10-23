"""The peony, printed in one go: back flat on the bed (the wall side), petals up, soft pink, no supports (every petal
rests on the one below: `petals`). The yellow stamens are a separate insert, printed on its own plate.

Parts: a thin floor under the bowl, a ring round the centre hole, a solid boss holding the keyhole (up +Y: the
insert takes the centre), the 81 petals. The insert is a plug through the hole from the back, a 45-degree flared
foot stopping it, stamens and carpels on top; on the wall, the wall holds it in.
"""
import math
import random
from functools import lru_cache
from pathlib import Path

from build123d import Align, Cone, Cylinder, Part, Pos, Rot, SlotCenterToCenter, Sphere, extrude, scale

from cadkit import bambu3mf, slicers
from cadkit.export import write_plates
from cadkit.mesh import Mesh
from cadkit.plates import Plate
from peony_wall import layout, petals
from peony_wall.params import Params

NAIL_D = 3.0  # nail shank
MN = (Align.CENTER, Align.CENTER, Align.MIN)


def keyhole_end(p: Params) -> float:
    """The slot's end arc centre on +Y: the nail's shank rests against the slot's top, key_at up from the centre."""
    return p.key_at + NAIL_D / 2 - p.key_shank_w / 2


def key_top(p: Params) -> float:
    return p.key_lip + p.key_head_room + p.printer.snap(p.key_head_d / 2 - p.key_roof_left / 2)


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


def hole(p: Params) -> Part:
    """The insert's way in from the back: a straight hole, flaring out 45 degrees at the back."""
    r = p.hole_r + p.fit_slide / 2
    return (Pos(0, 0, -1) * Cylinder(r, p.ring_t + 2, align=MN)
            + Pos(0, 0, -1) * Cone(r + p.flare + 1, r, p.flare + 1, align=MN))


def structure(p: Params) -> list[Mesh]:
    """What ties the petals together and hangs it: floor, ring round the hole, keyhole boss (cut later, with
    everything: the petals' fills reach into it)."""
    return [Mesh.from_shape(Cylinder(p.floor_r, p.floor, align=MN) - hole(p)),
            Mesh.from_shape(Cylinder(p.ring_r, p.ring_t, align=MN) - hole(p)),
            Mesh.from_shape(boss(p))]


def boss(p: Params) -> Part:
    """Solid round the whole keyhole (entry hole to the slot's top) and key_wall past it, for it to cut into."""
    end = keyhole_end(p)
    return Pos(0, end - p.key_len / 2, 0) * extrude(
        SlotCenterToCenter(p.key_len, p.key_head_d + 2 * p.key_wall, rotation=90), p.key_boss_t)


def parts(p: Params, fill_under: bool = True) -> list[Mesh]:
    """Every body in the flower's frame (centre on the axis, back at z = 0): structure, then the petals."""
    return structure(p) + [petals.placed(p, s, fill_under) for s in layout.specs(p)]


@lru_cache
def body(p: Params) -> Mesh:
    """Everything unioned into one mesh (B-rep fusing gave up on these petals: invalid, in pieces), with the
    insert's hole and the keyhole cut through whatever the fills put there."""
    whole = Mesh.union(parts(p), label="peony", color=p.color(p.slot_flower)) - hole(p)
    for c in keyhole(p):
        whole = whole - c
    return whole.drop_crumbs(1.0)


def centre_xy(p: Params) -> tuple[float, float]:
    return p.printer.bed / 2, (p.printer.bed_y or p.printer.bed) / 2


def make(p: Params) -> Mesh:
    """The peony in its print position: centred on the bed."""
    return body(p).translate((*centre_xy(p), 0))


@lru_cache
def insert(p: Params) -> Mesh:
    """The yellow insert, back on the bed: flared foot, plug up to the ring's top, stamens and carpels on it.
    Each stamen's tilt is clipped so its anther stays inside the hole: it goes in from the back."""
    r = p.hole_r - p.fit_slide / 2
    plug = Cone(r + p.flare, r, p.flare, align=MN) + Cylinder(r, p.ring_t, align=MN)
    rng = random.Random(p.seed)
    bits = []
    for k in range(p.stamens):
        f = math.sqrt((k + 0.5) / p.stamens)
        at = p.stamen_r[0] + (p.stamen_r[1] - p.stamen_r[0]) * f
        length = rng.uniform(*p.stamen_len)
        room = (r - 0.3 - p.anther[0] - at) / length  # sin of the tilt that puts the anther at the hole's edge
        tilt = min(layout.lerp(p.stamen_tilt, f) + rng.uniform(-4, 4), math.degrees(math.asin(min(room, 1))))
        tip = Rot(0, 0, k * layout.GOLD) * Pos(at, 0, p.ring_t - 0.4) * Rot(0, tilt, 0) * Pos(0, 0, length)
        bits.append(Rot(0, 0, k * layout.GOLD) * Pos(at, 0, p.ring_t - 0.4) * Rot(0, tilt, 0)
                    * Cylinder(p.stamen_d / 2, length, align=MN))
        bits.append(Pos(*tip.position) * anther(p))
    for k in range(5):  # carpels: low domes in the middle (their lower halves inside the plug)
        bits.append(Rot(0, 0, k * 72) * Pos(2.6, 0, p.ring_t) * scale(Sphere(1), (2.8, 2.2, 4.0)))
    whole = Mesh.union([Mesh.from_shape(b, tol=0.02) for b in [plug] + bits], label="stamens",
                       color=p.color(p.slot_insert))
    return whole.trimmed(0.0)


def anther(p: Params) -> Part:
    """An anther, upright whatever its stamen's tilt: a 45-degree cone out from a point, a dome on top."""
    r, h = p.anther
    dome = scale(Sphere(1), (r, r, h)) & Cylinder(r + 1, h + 1, align=MN)  # the upper half
    return Pos(0, 0, -r) * Cone(0.05, r, r, align=MN) + dome  # from a point: a tilted stamen leaves no ledge


def insert_placed(p: Params) -> Mesh:
    """The insert in the flower's frame: it's round and printed back-down, so the same."""
    return insert(p)


def write(p: Params, out: Path) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(out / "bambu_project_settings.config", list(p.filaments))
    stamens = insert(p).translate((*centre_xy(p), 0))
    slot = lambda name: p.slot_flower if name == "peony" else p.slot_insert
    write_plates([Plate("peony", 1, [("peony", make(p))]), Plate("stamens", 1, [("stamens", stamens)])],
                 out / "plates", out / "plates.csv", slot, settings=settings, combined="peony-wall")
    # to look at, not to print: the flower with the insert in place (printed together it'd swap every layer)
    s = slicers.active()
    at = (*centre_xy(p), 0)
    s.write_project(out / "plates" / f"peony_assembled{s.project_suffix}",
                    [("peony_assembled", [("peony", make(p), slot("peony")),
                                          ("stamens", insert_placed(p).translate(at), slot("stamens"))])], settings)
