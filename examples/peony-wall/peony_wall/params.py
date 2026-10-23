"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer
from cadkit.printer import default


@dataclass(frozen=True)
class Params:
    diameter: float = 203.0  # about 8" across, like the rose
    seed: int = 5  # the petals' small irregularities (lean, length, ruffle) come from this
    wall: float = 1.6  # petal thickness: four lines
    slope: float = 1.0  # the fill under each petal: run per rise (1 = 45 degrees)
    lean_out_max: float = 75.0  # past this a guard petal's ruffle crests roll over: no fill can help a face on top
    lean_in_max: float = 42.0  # curling in past this, a petal's own underside would overhang
    claw: float = 1.0  # how wide a petal's foot is, of its top: a narrow claw (0.5) leaves the fill under its top showing
    grid: tuple = (36, 73)  # mesh points along x across each petal (about 1.2 mm apart at the rim)

    # guard petals: a low ruffled skirt round the outside
    guards: int = 9
    guard_foot: float = 62.0
    guard_length: float = 44.0
    guard_lean: tuple = (52.0, 72.0)  # at the foot, at the rim (deg from upright)
    guard_half: float = 25.0  # half the angle each wraps round the axis (deg)
    guard_amp: tuple = (2.0, 2.8)  # ruffle height range
    guard_turn: float = 8.0  # each placed up to this far off even spacing (deg)

    # bowl petals: a golden-angle spiral from upright and curling in (innermost) to leaning out (outermost)
    bowl: int = 70
    bowl_feet: tuple = (24.0, 62.0)  # foot radius, innermost .. outermost
    bowl_length: tuple = (54.0, 42.0)
    bowl_lean0: tuple = (20.0, 52.0)  # lean at the foot
    bowl_lean: tuple = (-40.0, 40.0)  # lean at the rim: negative curls in over the centre
    bowl_half: tuple = (32.0, 22.0)
    bowl_amp: tuple = (1.6, 2.6)
    bowl_cup: tuple = (1.0, 3.0)  # cupped across the petal
    jitter: tuple = (8.0, 6.0, 4.0, 4.0)  # +- on rim lean, foot lean, length, half wrap

    # three inner petals folding across the opening, so only some of the yellow shows
    folds: tuple = (70.0, 190.0, 300.0)  # where they stand (deg round the axis)
    fold_foot: float = 25.0
    fold_length: float = 50.0
    fold_lean: tuple = (10.0, -42.0)
    fold_half: float = 26.0

    waves: tuple = (2.0, 3.2)  # ruffle waves across a petal
    scallop: float = 0.05  # how deep the rim's scallops are (fraction of the petal's length)

    # what ties it together and hangs it
    floor: float = 1.2  # a thin disc under the bowl, hidden by the petals
    floor_r: float = 62.0
    key_at: float = 70.0  # the nail, this far up +Y from the centre (the insert is at the centre), under the bowl
    key_wall: float = 3.0  # the boss round the keyhole, past its outline
    key_boss_t: float = 10.8  # 1.6 over the keyhole roof
    key_len: float = 14.0  # the rose's keyhole: entry hole to the slot's top
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6
    key_head_room: float = 3.2
    key_roof_left: float = 0.8

    # the yellow insert: a plug through the centre from the back, a 45-degree flared foot stops it
    hole_r: float = 20.0  # the plug's hole through the flower's centre (inside the innermost feet)
    flare: float = 2.5  # the foot flares this much wider at the back (45 degrees), still inside the feet
    ring_t: float = 8.0  # the pink ring round the hole, up to this height
    ring_r: float = 26.0
    fit_slide: float = 0.3  # diametral clearance round the plug (held by the wall, so a slide fit)
    stamens: int = 120  # dense, so the yellow reads as stamens, not a disc
    stamen_d: float = 1.6
    stamen_r: tuple = (6.0, 13.5)  # where they stand on the plug; tilts clip so tips stay in the hole (it goes in from the back)
    stamen_len: tuple = (7.0, 11.0)
    stamen_tilt: tuple = (8.0, 34.0)  # innermost .. outermost (deg from upright)
    anther: tuple = (1.3, 1.9)  # anther blob: radius, half height

    # AMS: soft pink for the flower, yellow for the insert (its own plate)
    filaments: tuple = (("PLA", "#F4A9BC"), ("PLA", "#F2B705"),  # soft pink, yellow
                        ("PLA", "#161616"), ("PLA", "#5A3A1E"))  # unused: whatever's in slots 3 and 4
    slot_flower: int = 1
    slot_insert: int = 2
    printer: Printer = field(default_factory=default)

    def __post_init__(self):
        for name in ("floor", "key_boss_t", "key_lip", "key_head_room", "ring_t"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))


P = Params()
