"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer

INCH = 25.4


@dataclass(frozen=True)
class Params:
    diameters_in: tuple = tuple(range(4, 18))  # a pencil hole per circle size, in inches: 4" to 17"
    t: float = 6.0  # thickness: stiff over the bar's length
    w: float = 26.0  # width of the bar and of each short arm
    arm_edge: float = 2 * INCH  # straight edge on each short arm, out past the hub
    bar_end: float = 10.0  # bar runs on this far past the last pencil hole
    pivot_d: float = 4.5  # the screw it turns on (#8 wood screw, 4.2 mm shank)
    hole_off: float = 10.0  # pencil holes sit this far in from the bar's straight edge
    throat_d: float = 2.0  # pencil tip pokes through this at the bottom, so the point sits on the hole's centre
    throat_h: float = 2.0
    sink_deg: float = 30.0  # from vertical: the cone above the throat that guides a sharpened pencil down
    bevel: float = 3.0  # straight edges bevelled on top (like a ruler) so the line shows right at the edge
    label_size: float = 5.0  # raised inch numbers beside the holes
    label_h: float = 0.6
    filament: int = 1  # AMS slot: orange, easy to see on wood
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so tops print whole."""
        for name in ("t", "throat_h"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        object.__setattr__(self, "label_h", self.printer.layers(self.label_h))
        if self.radii[0] - self.sink_r <= self.w:
            raise ValueError(f"smallest circle {self.diameters_in[0]}\" lands in the hub: start above "
                             f"{2 * (self.w + self.sink_r) / INCH:.1f}\"")

    @property
    def radii(self) -> list[float]:
        return [d * INCH / 2 for d in self.diameters_in]

    @property
    def arm(self) -> float:
        """Pivot to a short arm's tip."""
        return self.w + self.arm_edge

    @property
    def sink_r(self) -> float:
        """Radius of the guide cone at the top face."""
        from math import radians, tan
        return self.throat_d / 2 + (self.t - self.throat_h) * tan(radians(self.sink_deg))

    @property
    def bar_len(self) -> float:
        """Pivot to the bar's far end."""
        return self.hole_x(self.radii[-1]) + self.bar_end

    def hole_x(self, r: float) -> float:
        """Along the bar, where a hole sits so its centre is r from the pivot (it's hole_off off the edge line)."""
        return (r * r - self.hole_off ** 2) ** 0.5


P = Params()
