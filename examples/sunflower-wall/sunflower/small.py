"""The 10-inch flower, printed in one go: the same design scaled to the biggest the bed takes, every part stacked in
place as one object, colors by height: yellow with the front petals' orange beads (a swap on each layer the beads
cross), then black, then brown.

Changes from the 16-inch kit, only where a single print needs them:
- the front petals are filled down to the bed (they'd otherwise start over air above the arching back petals);
- the seed head sits on a hidden yellow riser just above the tallest petal, so the black never shares a layer with
  yellow (sharing would mean two color swaps per layer);
- no pins, sockets or seams; one keyhole, placed from the wall measurements (docs/measurements.md) so the flower
  hangs centered in its gap.
Thicknesses stay as they are (they're set by what prints well, not by the flower's size); seeds keep their size.
"""
import math
from dataclasses import replace
from pathlib import Path

from build123d import Align, Color, Compound, Cone, Cylinder, Part, Pos, Rot, SlotCenterToCenter, extrude

from cadkit import bambu3mf
from cadkit.export import write_plates
from cadkit.plates import Plate
from sunflower import layout
from sunflower.params import P, Params, Ring
from sunflower.parts import center, quarter

INCH = 25.4
GAP = (20 + 3 / 8) * INCH  # docs/measurements.md
NAIL_DOWN = 8 * INCH
NAIL_ABOVE_CENTER = GAP / 2 - NAIL_DOWN  # flower centered in the gap
NAIL_D = 3.0  # nail shank
TOWER_W, TOWER_BRIM = 30.0, 3.0  # prime tower width; the settings template's brim
TOWER_MARGIN = 1.0  # tower brim to the bed edge
KEY_LEN = 14.0  # entry hole to the slot's end
KEY_HEAD_ROOM = 3.2  # nail head height the cavity takes before its roof
ROOF_LEFT = 0.8  # flat strip left at the top of the 45-degree roof
YELLOW, ORANGE, BLACK, BROWN = Color(0.96, 0.77, 0.09), Color(0.91, 0.53, 0.16), center.BLACK, center.BROWN


def _layer(p: Params, z: float) -> float:
    return round(z / p.printer.layer) * p.printer.layer


def params(base: Params = P, diameter: float | None = None) -> Params:
    """The flower scaled across (radii, widths) to `diameter` (default: the bed's usable width, less 1 mm)."""
    s = (diameter or base.printer.usable - 1) / base.diameter
    ring = lambda g: Ring(g.r0 * s, g.r1 * s, g.width * s, tuple((r * s, z) for r, z in g.profile), g.drop)
    center_r = base.center_r * s
    center_t = _layer(base, base.center_t * s)
    return replace(base, back=ring(base.back), front=ring(base.front), hub_r=base.hub_r * s,
                   center_r=center_r, center_t=center_t, center_rb=center_r - center_t,
                   seed_gaps=tuple((r * s if r < 900 else r, g) for r, g in base.seed_gaps),
                   seed_dome=_layer(base, base.seed_dome * s),
                   bead_r=tuple(r * s for r in base.bead_r), bead_fade=base.bead_fade * s)


def key_angle(p: Params) -> float:
    """Behind the first front petal's root: the thickest place outside the riser."""
    return layout.front_angles(p)[0]


def riser_top(p: Params) -> float:
    """Above the tallest yellow (back ring + highest front midrib), on a layer."""
    top = p.back_t + max(z for _, z in p.front.profile)
    return math.ceil(top / p.printer.layer - 1e-9) * p.printer.layer


def _keyhole(p: Params) -> list:
    r_end = NAIL_ABOVE_CENTER - (p.key_shank_w - NAIL_D) / 2  # shank rests on the slot's end at the nail height
    r_in = r_end - KEY_LEN
    mid = (r_in + r_end) / 2
    at = Rot(0, 0, key_angle(p)) * Pos(mid, 0, 0)
    roof = p.key_head_d / 2 - ROOF_LEFT / 2
    return [at * Pos(0, 0, -1) * extrude(SlotCenterToCenter(KEY_LEN, p.key_shank_w), p.key_lip + 1),
            Rot(0, 0, key_angle(p)) * Pos(r_in, 0, -1) *
            Cylinder(p.key_head_d / 2, p.key_lip + 1, align=(Align.CENTER, Align.CENTER, Align.MIN)),
            at * Pos(0, 0, p.key_lip) * extrude(SlotCenterToCenter(KEY_LEN, p.key_head_d), KEY_HEAD_ROOM),
            at * Pos(0, 0, p.key_lip + KEY_HEAD_ROOM) *
            extrude(SlotCenterToCenter(KEY_LEN, p.key_head_d), _layer(p, roof), taper=45)]


def assembled(p: Params) -> Compound:
    """Centered on the flower axis, back on the wall at z = 0."""
    fill = [Rot(0, 0, a) * extrude(quarter.outline(p.front), p.back_t) for a in layout.front_angles(p)]
    base_top = p.back_t + p.front_t
    flare = p.center_rb - p.hub_r  # the head is wider than the hub: flare out at 45 degrees, not over air
    mn = (Align.CENTER, Align.CENTER, Align.MIN)
    riser = [Pos(0, 0, base_top) * Cone(p.hub_r, p.center_rb, flare, align=mn),
             Pos(0, 0, base_top + flare) * Cylinder(p.center_rb, riser_top(p) - base_top - flare, align=mn)]
    yellow = quarter.whole(p, "back") + fill + [Pos(0, 0, p.back_t) * quarter.whole(p, "front")] + riser
    orange = Part([s for a in layout.front_angles(p) for s in (Pos(0, 0, p.back_t) * Rot(0, 0, a) *
                                                                quarter.beads(p)).solids()])
    yellow = Part((Part(yellow.solids()) - _keyhole(p) - orange).solids())
    head_body, seeds = center.assembled(p, sockets=False).children
    black = Pos(0, 0, riser_top(p)) * head_body
    brown = Pos(0, 0, riser_top(p)) * seeds
    for body, name, col in ((yellow, "flower_yellow", YELLOW), (orange, "flower_orange", ORANGE),
                            (black, "flower_black", BLACK), (brown, "flower_brown", BROWN)):
        body.label, body.color = name, col
    return Compound(children=[yellow, orange, black, brown], label="sunflower_10in")


def center_xy(p: Params) -> tuple:
    """Where the flower's center lands in the print frame."""
    r = p.diameter / 2
    return (r, r)


def make(p: Params) -> Compound:
    """Print orientation: on the bed, inside the +X +Y corner (center at center_xy)."""
    cx, cy = center_xy(p)
    out = []
    for b in assembled(p).children:
        moved = Pos(cx, cy, 0) * b
        moved.label, moved.color = b.label, b.color
        out.append(moved)
    return Compound(children=out, label="sunflower_10in")


def filament_for(p: Params):
    slots = {"flower_yellow": p.slot_petals, "flower_orange": p.slot_beads, "flower_black": p.slot_center,
             "flower_brown": p.slot_seeds}
    return lambda name: slots[name]


def plan(p: Params) -> list[Plate]:
    """The whole flower on one plate, centered on the bed."""
    off = (p.printer.bed - p.diameter) / 2
    return [Plate("sunflower_10in", 1, [("sunflower_10in", Pos(off, off, 0) * make(p))])]


def tower(p: Params) -> tuple:
    """Prime tower (x, y, width) in the bed's front-left corner, the only room the round flower leaves."""
    at = TOWER_BRIM + TOWER_MARGIN
    return (at, at, TOWER_W)


def write(p: Params, out: Path) -> None:
    Path(out).mkdir(parents=True, exist_ok=True)
    settings = bambu3mf.write_settings(Path(out) / "bambu_project_settings.config", list(p.filaments),
                                       tower=tower(p))
    write_plates(plan(p), Path(out) / "plates", Path(out) / "plates.csv", filament_for(p), settings=settings)
