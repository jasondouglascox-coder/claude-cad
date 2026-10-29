"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
import math
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    foot_d: float = 40.0  # outside of the old glass, where the gallery's spring tabs grip it
    foot_h: float = 10.0  # how far it sits down into the gallery
    foot_t: float = 1.2  # wall where the tabs squeeze: three lines, so the foot doesn't crack
    body_h: float = 31.0  # straight Ø40 above the foot, round the LED candle
    neck_d: float = 26.0
    shoulder_deg: float = 45.0  # from vertical: the steepest a one-line wall leans in without sagging
    bend_r: float = 8.0  # both bends of the shoulder rounded at this radius (outside surface)
    height: float = 131.0
    wall: float = 0.42  # one line (Bambu's outer wall line width); 0.84 for two
    brim: float = 8.0  # brim width, outside the foot and inside it
    filament_white: int = 1  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so the top prints whole."""
        for name in ("foot_h", "height"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        if self.neck_h < 2 * self.bend_r:
            raise ValueError(f"neck {self.neck_h:.1f} mm tall: make height at least {self.height - self.neck_h + 2 * self.bend_r:.1f}")
        if self.foot_h + self.foot_t >= self.shoulder_z:
            raise ValueError(f"foot_h {self.foot_h} runs into the shoulder at {self.shoulder_z:.1f}")

    @property
    def shoulder_z(self) -> float:
        """Where the straight body would meet the shoulder, before rounding."""
        return self.foot_h + self.body_h

    @property
    def shoulder_top(self) -> float:
        """Where the shoulder would meet the neck, before rounding."""
        return self.shoulder_z + (self.foot_d - self.neck_d) / 2 / math.tan(math.radians(self.shoulder_deg))

    @property
    def neck_h(self) -> float:
        return self.height - self.shoulder_top


P = Params()
