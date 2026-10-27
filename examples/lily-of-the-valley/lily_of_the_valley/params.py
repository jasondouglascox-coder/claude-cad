"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

Plan coordinates are the wall's: x right, y up, the sprig centred near the origin. z is out of the wall (the print's
height: the back is on the bed)."""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer
from cadkit.printer import default


@dataclass(frozen=True)
class Params:
    height: float = 188.0  # the sprig, stem foot to its arch (about 70% of the 256 mm bed)

    # the stem: a Bezier through these, foot first, rising up the left and arching over to the right
    stem: tuple = ((-35.0, -95.0), (-30.0, -20.0), (-38.0, 40.0), (-5.0, 95.0), (40.0, 82.0))
    stem_r: tuple = (2.5, 1.4)  # foot, tip

    # the bells, foot first: (where on the stem 0..1, apex this far below it, and out to the right, size, hang deg
    # from straight down, + swings the mouth right)
    bells: tuple = ((0.16, 14.0, 16.0, 0.95, 8.0), (0.40, 13.0, 18.0, 1.0, 4.0), (0.55, 12.0, 20.0, 1.0, -2.0),
                    (0.71, 12.0, 17.0, 0.95, 2.0), (0.94, 12.0, 10.0, 0.8, 0.0))  # one small cup at the tip
    bell_r: float = 12.0  # body radius of a size-1 bell
    bell_len: float = 2.0  # apex to mouth, in bell radii
    bell_flat: float = 0.85  # out of the wall: the bell's depth / its width
    lobes: int = 6
    lobe: float = 0.16  # the rim's scallops: radius swing
    lobe_push: float = 0.35  # the lobe points reach past the rim by this many bell radii
    flare: float = 0.30  # the rim flares out by this many bell radii
    recess: float = 0.4  # the mouth's hollow: depth in bell radii (a wide cone, roof shallower than 45)
    horn: tuple = (2.0, 0.7)  # the two side lobes curling back in the wall's plane: radius at the rim, at the tip

    pedicel_r: tuple = (1.3, 1.2)  # at the stem, at the bell (the key bell's carries the sprig: see knock)
    bract: float = 1.6  # half-width of the small pointed leaf at each pedicel's foot

    # colour by part: the bells white down to the wall, the stem, pedicels and bracts green half-ovals green_h tall
    # (at least half-rounds); every layer up to green_h prints both, so one colour change a layer, accepted (2026-10-27)
    green_h: float = 4.0
    color_changes: int = 20
    bell_z: float = 6.0  # the bells' axis height

    key_bell: int = 2  # the keyhole hides under this bell (the one over the centre of mass)
    key_at: float = 6.6  # the nail rests this far down the bell's axis from its apex (the mouth's hollow is below)
    key_len: float = 6.0  # entry hole to the slot's top
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6
    key_head_room: float = 3.2
    key_roof_left: float = 0.8
    key_wall: float = 1.2  # solid round the keyhole, sides and roof

    # as it hangs: pulled straight out from the wall at its far end with this, the key bell's pedicel alone stays
    # under the strength of printed PLA along its lines
    knock: float = 1.0  # N (about 100 g)
    pla_strength: float = 45.0  # MPa

    # AMS: green and white PLA, no supports
    filaments: tuple = (("PLA", "#4E8A2E"), ("PLA", "#F2F2EE"),  # green, white
                        ("PLA", "#6E1A5E"), ("PLA", "#F4A6B8"))  # unused: whatever's in slots 3 and 4
    slot_green: int = 1
    slot_white: int = 2
    printer: Printer = field(default_factory=default)

    def __post_init__(self):
        for name in ("green_h", "key_lip", "key_head_room"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))


P = Params()
