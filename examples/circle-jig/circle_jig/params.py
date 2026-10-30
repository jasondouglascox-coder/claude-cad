"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer

INCH = 25.4


@dataclass(frozen=True)
class Params:
    radii_in: tuple = tuple(range(2, 21))  # a pencil hole every inch out from the screw: 2" to 20" (40" circle)
    split_after: int = 8  # the bar comes apart past this hole: the hub piece alone draws up to it
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
    tab_len: float = 6.0  # dovetail tab on the extension's end, dropped into the hub from above (half a bow-tie)
    tab_head: float = 14.0
    tab_neck: float = 8.0
    fit_tab: float = 0.0  # tab in its socket: the railroad's keystone fit test (0.05 and 0.10 were loose)
    label_h: float = 0.6
    filament: int = 1  # AMS slot: orange, easy to see on wood
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so tops print whole."""
        for name in ("t", "throat_h"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        object.__setattr__(self, "label_h", self.printer.layers(self.label_h))
        if self.radii[0] - self.sink_r <= self.w:
            raise ValueError(f"smallest radius {self.radii_in[0]}\" lands in the hub: start above "
                             f"{(self.w + self.sink_r) / INCH:.1f}\"")
        if self.split_after not in self.radii_in[:-1]:
            raise ValueError(f"split_after {self.split_after}: pick a hole from {self.radii_in[:-1]}")
        room = self.hole_x((self.split_after + 1) * INCH) - self.split_x
        if self.tab_len + self.fit_tab + self.sink_r + 1 > room:
            raise ValueError(f"tab {self.tab_len} mm long runs into the hole before the seam: at most "
                             f"{room - self.sink_r - 1 - self.fit_tab:.1f}")

    @property
    def radii(self) -> list[float]:
        return [n * INCH for n in self.radii_in]

    @property
    def split_x(self) -> float:
        """The seam across the bar: midway between the last hub hole and the first extension hole."""
        return (self.hole_x(self.split_after * INCH) + self.hole_x((self.split_after + 1) * INCH)) / 2

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
