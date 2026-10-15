"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass, field

from cadkit import Printer


@dataclass(frozen=True)
class Ring:
    """One ring of petals. Each petal runs radially from r0 (under the hub) to its tip at r1."""
    r0: float
    r1: float
    width: float  # widest point
    profile: tuple  # (r, top z) along the midrib, in the ring's own print frame
    drop: float  # how much lower the edges are than the midrib


@dataclass(frozen=True)
class Params:
    petals: int = 16  # per ring; a multiple of 4 so the four quarters are identical
    back: Ring = Ring(60, 205, 40, ((60, 5.8), (100, 5.8), (140, 4.6), (175, 2.8), (207, 1.2)), 1.6)
    front: Ring = Ring(60, 192, 40, ((60, 2.8), (83, 2.8), (90, 6.6), (98, 9.0), (115, 8.2), (150, 5.0),
                                     (194, 1.2)), 2.4)  # rises once clear of the head's flat underside
    petal_min: float = 1.0  # thinnest petal anywhere (edges, tips): 5 layers
    hub_r: float = 78.0  # hub disk under the seed head, split into quarter wedges
    back_t: float = 6.0  # back hub thickness; back petals stay below it
    front_t: float = 3.0  # front hub thickness; the seed head sits on it
    seam_gap: float = 0.3  # between neighbouring quarters' hub wedges

    # seed head
    center_r: float = 90.0  # top rim radius
    center_rb: float = 80.0  # bottom radius: a 45-degree bevel up to the rim lets petals rise out from under it
    center_t: float = 10.0  # black body; seeds sit on top
    seed_c: float = 2.55  # Vogel spacing: seed i at r = c * sqrt(i), angle i * golden angle
    seed_zones: tuple = ((14.0, 2.2), (68.0, 3.8), (999.0, 2.6))  # (out to radius, seed diameter)
    seed_h: tuple = (2.4, 1.6)  # seed height at the middle and at the rim (a gentle dome)
    seed_taper: float = 14.0  # degrees
    seed_edge: float = 2.5  # bare black rim

    # snap pins (printed flat: profile in the print plane, pin_t thick)
    pin_r: float = 55.0  # radius of the pin circle
    pin_w: float = 4.4  # shank width (radial in the assembly)
    pin_t: float = 3.2  # print thickness (tangential in the assembly)
    pin_lip: float = 1.0  # head overhang each side
    pin_head: float = 1.6  # head height, recessed flush into the back hub
    pin_barb: float = 0.5  # barb overhang each side
    pin_tip: float = 2.4  # barb to tip
    pin_slot_w: float = 1.6  # split between the barb arms
    pin_slot_len: float = 10.0  # long arms bend gently (layout.pin_strain)
    throat: float = 1.2  # seed head floor the barbs snap over
    pin_play: float = 0.3  # barb clearance above the throat: three stacked prints add up
    fit: float = 0.2  # total slide clearance in slots (from examples/fit-coupon)

    # keyhole (in each back quarter's hub, on its bisector)
    key_r: tuple = (32.0, 46.0)  # entry hole center, top of the slot
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6
    screw: tuple = (8.5, 3.0, 4.0)  # pan head diameter, head height, shank diameter (for the clash test)

    # AMS slots (PLA) and display colors
    filaments: tuple = (("PLA", "#E8862A"), ("PLA", "#F5C518"), ("PLA", "#161616"), ("PLA", "#5A3A1E"))
    slot_petals: int = 2  # yellow
    slot_pins: int = 2
    slot_center: int = 3  # black
    slot_seeds: int = 4  # brown
    printer: Printer = field(default_factory=Printer)

    @property
    def pitch(self) -> float:
        return 360.0 / self.petals

    @property
    def diameter(self) -> float:
        return 2 * max(self.back.r1, self.front.r1)


P = Params()
