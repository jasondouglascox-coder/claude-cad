"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The gnome stands on z = 0 with its face to -Y. Three prints: the body (black boots, orange robe, white beard and
hair, one colour over the other by height), the witch hat (brim on the bed: black, an orange band, black) and the
pink nose, which press-fits onto a peg on the face."""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer
from cadkit.printer import default

INCH = 25.4


@dataclass(frozen=True)
class Params:
    height: float = 2 * INCH  # boots to the hat's tip, assembled

    # the mini tree's top goes up a round hole in the base, ending in a pointed roof (prints without support)
    hole_d: float = 0.5 * INCH
    hole_depth: float = 18.0  # to where the roof starts
    hole_roof: float = 40.0  # deg from vertical

    # the body, by height: black boots to boot_h, orange robe to robe_h, white beard and hair to shoulder_h,
    # where the hat's brim sits; a white cone (the head) goes on up inside the hat
    boot_h: float = 2.4
    robe_h: float = 11.0
    shoulder_h: float = 29.0
    base_r: float = 12.5  # the boots' ring and the robe's hem
    robe_top_r: float = 11.0
    toe: float = 3.0  # each boot's toe sticks out this far in front, toe_apart deg either side of the front
    toe_apart: float = 20.0
    toe_w: float = 14.0  # deg: each toe's half-width round the ring
    hair_r: float = 15.0  # sides and back at the fullest
    hair_top_r: float = 13.5  # ... rounding in to this at the shoulder, under the brim
    beard_r: float = 17.5  # the beard's front at its fullest, from its 45-degree flare up to beard_z
    beard_z: float = 18.0
    face_r: float = 13.0  # the front at the nose: the beard rounds in to it at nose_z
    strands: int = 40  # ridges round the beard and hair
    strand: float = 0.4
    flare: float = 0.95  # the most anything widens per mm up (under 45 degrees: 1.0)

    head_r: float = 9.0  # the head cone at the shoulder: the hat's socket fits over it, no clearance
    head_h: float = 6.0
    head_angle: float = 35.0  # deg from vertical, the head's sides and the socket's

    # the hat (its own z: brim on the bed)
    brim_r: float = 19.0
    brim_t: float = 1.2
    band_h: float = 2.6
    band_r: float = 11.1
    crown_r: float = 10.5  # just above the band
    tip_r: float = 0.6
    lean_from: float = 9.0  # the crown bends back from this height (its own z)
    lean: float = 0.055  # the bend: offset grows lean * (z - lean_from)^2 (outer side kept under 45 degrees)
    hat_wall: float = 1.0  # the least wall round the socket

    # the nose: a ball cut flat at the back, on a teardrop peg from the face (point down, so it prints unsupported)
    nose_r: float = 4.2
    nose_back: float = 2.0  # the flat back is this far behind the ball's centre
    nose_z: float = 24.6  # its top just under the brim
    peg_r: float = 1.3
    peg_len: float = 3.0
    peg_angle: float = 40.0  # deg from vertical, the teardrop's flanks
    nose_fit: float = 0.0  # diametral clearance: none, a squeeze (the user's choice)
    peg_room: float = 0.2  # the hole is this much deeper than the peg is long, so the back seats flat

    ring: int = 144  # points round each section
    dz: float = 0.2  # section spacing

    # AMS: as loaded for the sunflower, yellow and brown swapped for white and pink
    filaments: tuple = (("PLA", "#F07A1A"), ("PLA", "#F2F2EE"), ("PLA", "#1C1C1C"), ("PLA", "#F4A6B8"))
    slot_orange: int = 1
    slot_white: int = 2
    slot_black: int = 3
    slot_pink: int = 4
    printer: Printer = field(default_factory=default)

    def __post_init__(self):
        for name in ("height", "boot_h", "robe_h", "shoulder_h", "brim_t"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        object.__setattr__(self, "band_h", self.printer.layers(self.band_h))

    @property
    def hat_h(self) -> float:
        return self.height - self.shoulder_h

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))


P = Params()
