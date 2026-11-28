"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The sheep, from behind: an arc-shaped slot in the back of its head, 30 mm across and 5 mm tall at the center, its
top 3 mm under the top of the head, going in at least 5 mm. The antlers are a flat plate that sits against the back
of the head, with a nub that shoves into the slot. Y = 0 is the bottom of the slot (and of the plate), +Y is the
sheep's up, X across, centered on X = 0 until print time."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # the sheep (measured by the user, 2026-11-27)
    slot_h: float = 5.0  # slot height at its center
    slot_to_top: float = 3.0  # slot top to the top of the head, on the center line
    head_r: float = 30.0  # the head's top arc, seen from behind: a guess from the photos (chord 30 -> ~4 mm sag)
    # the nub: a short block, not the whole slot, so the slot's curve doesn't matter
    nub_w: float = 5.0  # along the slot
    nub_h: float = 5.4  # across the slot, centered on it: fit tab 3 (2026-11-27); 4.8 was too loose
    nub_depth: float = 5.0  # into the slot (it goes at least 5 mm deep)
    nub_chamfer: float = 0.6  # lead-in on the tip
    # the fit tabs: one nub per height on a small handle, notches on top count 1, 2, 3...
    fit_heights: tuple = (5.0, 5.2, 5.4, 5.6, 5.8)
    tab_w: float = 12.0
    tab_h: float = 12.0
    tab_t: float = 2.0
    notch_w: float = 1.0
    notch_d: float = 2.0
    # the plate
    t: float = 4.0  # thickness: 20 layers, stiff in PETG
    band_half: float = 16.0  # the band behind the head, out to here each side
    band_h: float = 8.0  # band from the slot bottom to its top on the center line: level with the head top, hidden
    span: float = 82.0  # antler tip to tip (sheep is just shy of 3.5" = 88 mm across the ears)
    rise: float = 45.0  # top tine above the top of the head
    root_x: float = 8.0  # where each beam leaves the band
    beam_w: float = 5.5  # beam width at the root, tapering to tip_w
    tine_w: float = 4.5  # tine width where it leaves the beam
    tip_w: float = 3.2  # every tip: 8 lines of 0.4 (refused under 6)
    smooth: float = 1.5  # round on the inside corners where tines join
    # the AMS lite (type, color) per slot: brown PETG is slot 2, as for the remote cover
    filaments: tuple = (("PETG", "#8A8A8A"), ("PETG", "#5A3A1E"), ("PLA", "#000000"), ("PLA", "#6F4A2A"))
    filament_brown: int = 2  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so the plate and nub tops print whole."""
        for name in ("t", "nub_depth", "tab_t"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        if self.tip_w < 6 * self.printer.nozzle:
            raise ValueError(f"tip_w {self.tip_w} is under 6 lines of {self.printer.nozzle}: tips would snap off")
        if not self.root_x + self.beam_w < self.span / 2:
            raise ValueError(f"span {self.span} too narrow for roots at {self.root_x}")

    @property
    def bottom(self) -> float:
        """The plate's bottom edge: the slot bottom, or the nub's if it's taller than the slot (centered on it)."""
        return min(0.0, (self.slot_h - self.nub_h) / 2)

    @property
    def head_top(self) -> float:
        """Top of the sheep's head on the center line, above the slot bottom."""
        return self.slot_h + self.slot_to_top

    @property
    def height(self) -> float:
        return self.head_top + self.rise


P = Params()
