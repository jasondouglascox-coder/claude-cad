"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The flower lies back down on the bed (the wall side), centred on the origin, z out of the wall. Colours by height:
yellow petals up to black_z, a thin black disk across the head, the brown ring on that (2 colour changes)."""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer
from cadkit.printer import default

INCH = 25.4


@dataclass(frozen=True)
class Ring:
    """A ring of petals, each running out from r0 (under the head) to its tip at r1."""
    r0: float
    r1: float
    width: float  # widest
    mid: tuple  # (t, height) along the midrib, t = 0 at r0 .. 1 at the tip
    edge: tuple  # (t, height) along the edges


@dataclass(frozen=True)
class Params:
    diameter: float = 3 * INCH  # tip to tip: smaller than the 4" roses

    # two rings of pointed petals, the front ring over the back ring's gaps; solid down to the bed
    petals: int = 12  # per ring
    # widths: neighbours in a ring overlap (just touching leaves edges meeting edge to edge)
    # every petal's top angles down to the wall at its edges and tip (petal() keeps one layer there)
    back: Ring = Ring(10.0, 38.1, 12.0, ((0.0, 1.6), (0.4, 1.6), (1.0, 0.0)), ((0.0, 0.0), (1.0, 0.0)))
    # the front petals rise to black_z under the head's rim and sweep down to the tip; their sides run down into
    # the back petals
    front: Ring = Ring(10.0, 34.6, 10.5, ((0.0, 4.0), (0.27, 4.0), (0.6, 2.2), (1.0, 0.0)),
                       ((0.0, 0.0), (1.0, 0.0)))
    vary: tuple = (0.06, 0.08)  # petals up to this much shorter, narrower than their ring's
    petal_shape: tuple = (0.85, 0.75)  # half-width ~ sin(pi t^a)^b: widest a little in from the root, pointed tip
    veins: int = 3  # lengthwise grooves across each petal
    vein_depth: float = 0.2  # one layer

    # the head: a yellow riser under it to black_z, a black disk black_t thick, the brown ring on that, its side
    # angling up at `side` all the way from the petals to the brown's top (no straight-up edges)
    head_r: float = 16.5  # about 43% of the flower across, as in the photo
    eye_r: float = 5.0  # the black eye left open in the middle of the brown ring
    black_z: float = 4.0
    black_t: float = 0.4  # two layers
    side: float = 45.0  # deg from level
    # the brown ring's height above the black: (r, h) control points, eased between; the inner wall drops straight
    # to the black floor (the eye sunk in); outside, the side's slope takes over
    brown: tuple = ((5.0, 1.0), (7.5, 3.0), (10.5, 3.4), (14.0, 2.8), (16.5, 2.0))
    # texture: diamonds where the two spirals cross, one on every seed of Vogel's sunflower spiral
    seed_c: float = 1.15  # seed k at r = seed_c * sqrt(k)
    spirals: tuple = (21, 34)  # the crossing families (Fibonacci numbers)
    texture: float = 0.6  # the diamonds' height
    texture_edge: float = 1.2  # the texture fades out this close to the ring's edges

    # keyhole under the head (the nail above the centre, so it hangs plumb), its roof under the eye
    hang_y: float = 6.0  # the nail's centre, above the flower's centre
    key_len: float = 6.0  # entry hole to the slot's top
    key_head_d: float = 8.0
    key_shank_w: float = 4.6
    key_lip: float = 1.2
    key_head_room: float = 2.0
    key_skin: float = 0.6  # least solid between the keyhole and the front

    # the plate: per_plate flowers in a square pitch apart, the prime tower in the middle
    per_plate: int = 4
    pitch: float = 96.0
    tower_w: float = 30.0
    color_changes: int = 2  # yellow to black, black to brown: accepted (the budget is 1)

    # AMS: as loaded for the big sunflower
    filaments: tuple = (("PLA", "#E8862A"), ("PLA", "#F5C518"), ("PLA", "#161616"), ("PLA", "#5A3A1E"))
    slot_yellow: int = 2
    slot_black: int = 3
    slot_brown: int = 4
    printer: Printer = field(default_factory=default)

    def __post_init__(self):
        for name in ("black_z", "black_t", "key_lip", "key_head_room"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))

    @property
    def brown_z(self) -> float:
        """Where the brown starts: on the black."""
        return self.black_z + self.black_t


P = Params()
