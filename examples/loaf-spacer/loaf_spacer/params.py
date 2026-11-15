"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The pan's inside cross-section, from the bottom up: bottom_w wide, straight up to wall_h, out to the sides
(about 45 degrees) until slant_top_h, where it's top_w wide, then straight up to rim_h."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    bottom_w: float = 65.0  # pan floor, inside
    wall_h: float = 20.0  # straight wall before the slant
    slant_top_h: float = 35.0  # where the slant ends
    top_w: float = 94.0  # inside width from slant_top_h up to the rim
    rim_h: float = 60.0  # pan depth
    fit: float = 0.3  # gap to the pan wall on each side, so it drops in without catching
    above_rim: float = 5.0  # the full-width sheet stands this far above the rim
    tab_w: float = 40.0  # pull tab, centered, on top of the sheet
    tab_h: float = 30.0
    hole_d: float = 22.0  # finger hole through the tab
    corner_r: float = 3.0  # sheet's top corners and where the tab meets the sheet
    tab_r: float = 8.0  # tab's top corners
    t: float = 0.8  # sheet thickness: 4 layers, the thinnest that stays a sheet
    filament_black: int = 3  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        """The thickness lands on the printer's layers (yours, from cadkit.settings), so the top prints whole."""
        object.__setattr__(self, "t", self.printer.snap(self.t))
        if not self.wall_h < self.slant_top_h < self.rim_h or self.top_w <= self.bottom_w:
            raise ValueError(f"pan profile doesn't climb and widen: wall_h {self.wall_h}, "
                             f"slant_top_h {self.slant_top_h}, rim_h {self.rim_h}, {self.bottom_w} -> {self.top_w}")
        if self.hole_d >= min(self.tab_w, self.tab_h) - 2 * 4 * self.printer.nozzle:
            raise ValueError(f"hole_d {self.hole_d} leaves less than 4 lines of tab around it")

    @property
    def sheet_h(self) -> float:
        """Top of the full-width sheet."""
        return self.rim_h + self.above_rim

    @property
    def height(self) -> float:
        return self.sheet_h + self.tab_h

    @property
    def hole_center_h(self) -> float:
        return self.sheet_h + self.tab_h / 2


P = Params()
