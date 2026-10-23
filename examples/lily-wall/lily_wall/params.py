"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer
from cadkit.printer import default


@dataclass(frozen=True)
class Params:
    diameter: float = 180.0  # about 70% of the 256 mm bed
    wall: float = 1.6  # tepal thickness: four lines
    grid: tuple = (64, 25)  # mesh points along x across each tepal

    # six tepals, alternating outer (the sepals: narrower) and inner; (outer, inner) pairs
    tepals: int = 6
    length: tuple = (101.0, 104.4)  # along the midrib, foot to tip
    width: tuple = (26.1, 31.3)  # at the widest
    foot: tuple = (11.3, 10.4)  # from the centre
    lean_tip: tuple = (145.0, 144.5)  # deg from upright: past 90 it recurves down, to the bed at the tip
    level: float = 0.4  # it rises straight out of the throat and is level (90 deg) this far along
    convex: float = 0.45  # the edges curl down from the midrib: drop = convex * half-width * v^2
    ripple: float = 0.87  # wavy margins: height
    ripples: float = 5.0  # waves along a tepal
    point: float = 6.0  # how fast the width closes to the tip (higher: a longer, finer point)

    # colour by height: white below, purple above, the long fade between (whole layers, one swap each)
    seam_at: float = 0.66  # of the tepals' height
    band: float = 8.0  # the fade's height (40 layers)

    # centre
    boss_r: tuple = (17.0, 12.0)  # the throat's floor: a solid cone holding the keyhole, bed .. top
    boss_t: float = 11.0
    stamens: int = 6
    stamen_d: float = 1.8
    stamen_len: float = 40.0
    stamen_tilt: float = 18.0  # deg from upright, out between the tepals
    anther: tuple = (1.4, 4.5)  # radius, half length
    pistil_d: float = 2.4
    pistil_len: float = 43.5
    stigma_r: float = 2.4

    key_len: float = 10.0  # entry hole to the slot's top (short: the throat is small)
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6
    key_head_room: float = 3.2
    key_roof_left: float = 0.8

    # AMS: white and purple PLA (supports print in them too)
    filaments: tuple = (("PLA", "#F2F2EE"), ("PLA", "#6E1A5E"),  # white, purple
                        ("PETG", "#8A8A8A"), ("PETG", "#5A3A1E"))  # unused: whatever's in slots 3 and 4
    slot_white: int = 1
    slot_purple: int = 2
    printer: Printer = field(default_factory=default)

    def __post_init__(self):
        for name in ("boss_t", "key_lip", "key_head_room", "band"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))

    @property
    def layers(self) -> int:
        """Layers in the fade."""
        return round(self.band / self.printer.layer)


P = Params()
