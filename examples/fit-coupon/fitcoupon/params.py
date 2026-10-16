"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    peg_d: float = 5.0  # the pin being fitted
    peg_h: float = 8.0
    clearances: tuple = (0.1, 0.2, 0.3)  # diametral gap per hole: pick the one that slides, put it in your project
    pitch: float = 14.0  # hole to hole
    plate_w: float = 18.0
    plate_t: float = 3.0  # a layer multiple, so the color seam lands on a layer boundary
    mark_w: float = 1.2  # one raised bar per variant number: 1, 2, 3 bars
    mark_l: float = 4.0
    mark_gap: float = 0.8
    mark_h: float = 0.6
    edge: float = 2.0
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so tops and the color seam print whole."""
        for name in ("peg_h", "plate_t"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        for name in ("mark_h",):  # stacked on a height above
            object.__setattr__(self, name, self.printer.layers(getattr(self, name)))

    @property
    def plate_l(self) -> float:
        return self.pitch * len(self.clearances) + self.edge


P = Params()
