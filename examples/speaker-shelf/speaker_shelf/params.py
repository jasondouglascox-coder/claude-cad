"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # The banister, by ruler (docs/measurements.md); the coupon finds the real numbers.
    rail: float = 13.0  # square tube
    rail_gap: float = 86.0  # face to face between two rails

    # Rail fork: push each slot onto a rail; the snug one is the rail's real size.
    fork_slots: tuple = (12.4, 12.6, 12.8, 13.0, 13.2, 13.4, 13.6, 13.8)
    fork_tooth: float = 4.0  # between slots, and at each end
    fork_depth: float = 15.0  # slot depth: past the rail's far face
    fork_spine: float = 9.0  # solid strip behind the slots, carrying the labels
    fork_h: float = 8.0

    # Gap gauge: a bar with stepped ends; push it between two rails, the deepest step in gives the gap.
    gap_steps: tuple = (84.0, 84.5, 85.0, 85.5, 86.0, 86.5, 87.0, 87.5, 88.0)
    gap_step_d: float = 5.0  # depth of each step
    gap_h: float = 5.0

    label_size: float = 3.5
    label_depth: float = 0.6  # engraved into the top
    filament_black: int = 3  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        for name in ("fork_h", "gap_h"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        object.__setattr__(self, "label_depth", self.printer.layers(self.label_depth))

    @property
    def fork_l(self) -> float:
        return sum(self.fork_slots) + self.fork_tooth * (len(self.fork_slots) + 1)

    @property
    def gap_d(self) -> float:
        return self.gap_step_d * len(self.gap_steps)


P = Params()
