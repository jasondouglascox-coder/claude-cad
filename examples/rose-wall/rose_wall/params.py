"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass, field, replace

from build123d import Color

from cadkit import Printer
from cadkit.printer import default


@dataclass(frozen=True)
class Params:
    diameter: float = 203.0  # about 8" across: what the tests hold the rose to

    # outer petals (24, on a golden-angle spiral, feet spreading out from the centre)
    petals: int = 24
    wall: float = 1.6  # petal thickness: four lines
    foot_r: float = 72.3  # the outermost petal's foot, from the centre
    length: tuple = (26.6, 60.0)  # along the petal's side from its foot, innermost .. outermost
    lean: tuple = (45.0, 135.0)  # lean at the tip (deg from upright), innermost .. outermost: past 90 rolls back down
    bend: float = 1.4  # how the lean grows along the petal (lean ~ t ** bend): lower bends sooner
    wrap: tuple = (80.0, 42.0)  # half the angle each petal wraps round the centre (deg), innermost .. outermost
    point: float = 0.45  # how sharp each petal's tip is: 0 round
    filled: int = 0  # outer petals 1..filled curl over other petals: a hidden 45-degree fill under each, no support

    # centre: a funnel of small, tightly wrapped petals whose rims step down into the middle
    centre_petals: int = 8
    centre_gap: float = 0.9  # between neighbouring centre petals
    centre_first: float = 2.0  # the innermost one's foot, from the centre
    centre_top: float = 23.3  # the outermost centre petal's length (about the first outer petal's rim)
    centre_drop: float = 8.9  # the innermost centre petal this much shorter: the funnel
    centre_lean: tuple = (8.0, 18.0)  # lean at the rim (deg), innermost .. outermost
    centre_lip: float = 25.0  # extra outward roll over the last 15% of each centre petal (deg)
    centre_wrap: tuple = (150.0, 110.0)  # half wrap (deg), innermost .. outermost
    centre_point: float = 0.12
    centre_turn: float = 40.0  # the centre petals' spiral starts this far round from the outer petals'
    centre_backs: bool = False  # keep each centre petal's whole wrap (the tip's lens otherwise trims its back off)
    nub: tuple = ()  # (foot r, top r, how far under the innermost centre rim): a plug in the very middle; () none

    # what holds it together and hangs it
    floor: float = 1.2  # thin pads under each petal, tying their feet into one piece (never past a foot)
    base_t: float = 11.0  # a solid cone under the centre, for the keyhole
    key_len: float = 14.0  # entry hole to the slot's top
    key_head_d: float = 9.5
    key_shank_w: float = 4.6
    key_lip: float = 1.6
    key_head_room: float = 3.2
    key_roof_left: float = 0.8  # flat strip at the top of the 45-degree roof

    # AMS: red PLA for the rose, PETG only as the support interface under the curled petals
    filaments: tuple = (("PLA", "#9E0D14"), ("PETG", "#F0F0F0"),  # the rose, the support interface
                        ("PLA", "#161616"), ("PLA", "#5A3A1E"))  # unused: whatever's in slots 3 and 4
    slot_rose: int = 1
    slot_support: int = 2
    printer: Printer = field(default_factory=default)

    # the plate: one rose in the middle, or four in a square `pitch` apart (centre to centre) round the prime tower
    name: str = "rose"
    per_plate: int = 1
    pitch: float = 0.0

    def __post_init__(self):
        for name in ("floor", "base_t", "key_lip", "key_head_room"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))

    def color(self, slot: int) -> Color:
        c = self.filaments[slot - 1][1]
        return Color(*(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)))

    @property
    def centre_r(self) -> float:
        """Where the centre ends and the outer petals' feet begin."""
        return self.centre_first + self.centre_petals * (self.wall + self.centre_gap)


P = Params()


def small(p: Params = P) -> Params:
    """The rose at half size, four to a plate. Only the plan halves: the walls (four lines), the centre's gaps and
    the nail stay full size, so the centre has four petals, not eight. Its base drops to 6 mm (a smaller keyhole
    with a flat roof) to stay under them, and so the base doesn't read as a floor a few mm down, the centre petals
    keep their backs, stand taller and lean out together (you can't see down between them), round a nub. Supports
    only on the outside: the 18 inner curls hang over other petals and rest on hidden fills; the outer five hang
    over bare bed and keep theirs."""
    s = 0.5
    return replace(p, diameter=p.diameter * s, foot_r=p.foot_r * s, length=tuple(x * s for x in p.length),
                   centre_petals=4, centre_first=p.centre_first * s,
                   centre_top=13.5, centre_drop=3.5, centre_lean=(30.0, 33.0), centre_lip=10.0,
                   centre_wrap=(175.0, 165.0), centre_backs=True, nub=(2.0, 0.8, 1.5),
                   base_t=6.0, key_len=8.0, key_head_d=8.0, key_lip=1.2, key_head_room=2.4, key_roof_left=7.6,
                   filled=18, name="small_roses", per_plate=4, pitch=120.0)


SMALL = small()
