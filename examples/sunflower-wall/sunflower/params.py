"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The flower is drawn at 400 mm across; `flower.params()` scales it to the biggest the bed takes. Only radii and
widths scale: thicknesses and heights are set by what prints well, so they stay as written here.
"""
from dataclasses import dataclass, field

from build123d import Color

from cadkit import Printer


@dataclass(frozen=True)
class Ring:
    """One ring of petals. Each petal runs radially from r0 (under the hub) to its tip at r1."""
    r0: float
    r1: float
    width: float  # widest point
    profile: tuple  # (r, top z) along the midrib, bed at z = 0
    drop: float  # how much lower the edges are than the midrib
    edge: tuple | None = None  # (r, edge z) instead of a fixed drop: edges come down to these heights


BACK = Ring(60, 205, 40, ((60, 5.8), (100, 5.8), (140, 4.6), (175, 2.8), (207, 1.2)), 1.6)


@dataclass(frozen=True)
class Params:
    petals: int = 16  # per ring
    back: Ring = BACK
    # front petals: level under the head, at the head's rim (center_r) as high as the yellow goes, then falling
    # to the tip at the plate; across, their edges come down onto the back petals' midribs
    front: Ring = Ring(60, 192, 40, ((60, 12.0), (90, 12.0), (98, 12.0), (115, 10.9), (150, 6.5), (194, 1.2)),
                       0.0, edge=BACK.profile)
    petal_min: float = 1.0  # thinnest petal anywhere (edges, tips): 5 layers
    petal_veins: int = 9  # lengthwise grooves across each petal
    vein_depth: float = 0.4  # two layers
    # orange beads down the front petals' middle valleys: a warm shade that reads as depth from a few feet
    bead_valleys: tuple = (2, 3, 4, 5, 6)  # the middle five of the nine valleys (0 and 8 at the edges)
    bead_r: tuple = (98.0, 130.0)  # from the top of the arch outward: lower valleys would cost more color swaps
    bead_w: float = 1.2  # widest: three lines
    bead_w_end: float = 0.4  # one line where each bead fades in and where it tapers out
    bead_fade: float = 6.0  # fade-in length
    bead_t: float = 0.4  # two layers, flush with the petal top
    hub_r: float = 78.0  # hub disk under the seed head
    back_t: float = 6.0  # back hub thickness; back petals stay below it
    front_t: float = 3.0  # front hub thickness (inside the back hub and the riser)

    # seed head: a thin black floor out to the rim, on a hidden yellow riser at the front petals' top; the seeds
    # run out to the rim and dome up from there
    center_r: float = 90.0  # rim radius: the front petals meet the head here
    center_t: float = 1.0  # black floor: five layers, showing only between the seeds
    seed_c: float = 2.55  # Vogel spacing: seed i at r = c * sqrt(i), angle i * golden angle
    seed_gaps: tuple = ((14.0, 0.8), (68.0, 0.6), (999.0, 0.9))  # (out to radius, black gap between seeds)
    seed_narrow: float = 0.8  # seeds narrowed across the radius: diamonds pointing in and out
    seed_top: float = 0.35  # pyramid top: the top face is this fraction of the base (more on tiny seeds)
    seed_min_edge: float = 0.6  # cell corners closer than this merge (no slivers)
    seed_shoulder: float = 0.6  # straight-sided column of a rim seed, below its pyramid
    seed_pyramid: float = 1.4  # pyramid height
    seed_dome: float = 9.0  # middle seeds' columns this much taller than the rim's: the head domes up
    seed_edge: float = 0.6  # bare black at the rim: a seed gap

    # keyhole behind the first front petal's root (flower.py places it from the wall measurements)
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6

    # AMS slots (PLA) and display colors
    filaments: tuple = (("PLA", "#E8862A"), ("PLA", "#F5C518"), ("PLA", "#161616"), ("PLA", "#5A3A1E"))
    slot_petals: int = 2  # yellow
    slot_center: int = 3  # black
    slot_seeds: int = 4  # brown
    slot_beads: int = 1  # orange
    printer: Printer = field(default_factory=Printer)

    def color(self, slot: int) -> Color:
        """Display color of AMS slot `slot` (from 1)."""
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))

    @property
    def pitch(self) -> float:
        return 360.0 / self.petals

    @property
    def diameter(self) -> float:
        return 2 * max(self.back.r1, self.front.r1)

    @property
    def front_top(self) -> float:
        """The tallest yellow: the front petals at the head's rim, where the black starts."""
        return max(z for _, z in self.front.profile)


P = Params()
