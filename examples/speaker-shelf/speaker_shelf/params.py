"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # The banister, from the fit coupon (docs/measurements.md).
    rail: float = 12.3  # clip jaw spacing: the fork's 12.4 slot slid on right, the user asked one step tighter
    rail_gap: float = 86.0  # face to face, the real gap (gap gauge)
    clip_gap: float = 88.0  # the clip arms sit as if the rails were 88 apart: about 1 mm play each side (user's call)
    rail_clear: float = 0.5  # floor and walls between the rails to each rail's inner face

    # The speaker and the shelf (rail frame: rails at y = 0, +y toward the back). The speaker sits centered on the
    # rail line, its middle between the rails, which are its side walls there.
    speaker_w: float = 83.0  # along the banister
    speaker_d: float = 75.0
    speaker_clear: float = 0.5  # each side, in the pocket
    floor_t: float = 3.0
    wall: float = 1.6  # pocket walls (4 lines)
    wall_h: float = 12.0  # pocket walls, floor included
    clip_h: float = 10.0  # front jaw, arm and hook
    jaw_t: float = 3.0  # front jaw, in front of each rail
    arm_t: float = 2.0  # the flexing arm along each rail's outer face
    arm_gap: float = 0.1  # arm to rail outer face
    arm_slot: float = 0.6  # frees the arm from the floor and jaw
    arm_free: float = 42.0  # flexing length, root to arm end
    arm_root: float = 8.0  # at least this much of the arm stays fused to the floor
    hook_depth: float = 5.3  # behind the rail, from the arm's design face: 4.3 on the real rail
    hook_tip: float = 0.8  # the hook's tip, before its 45-degree lead-in
    tab: float = 4.0  # finger tab on the arm end, to pull it open
    tab_w: float = 3.0

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
        for name in ("fork_h", "gap_h", "floor_t", "wall_h", "clip_h"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        object.__setattr__(self, "label_depth", self.printer.layers(self.label_depth))

    @property
    def fork_l(self) -> float:
        return sum(self.fork_slots) + self.fork_tooth * (len(self.fork_slots) + 1)

    @property
    def gap_d(self) -> float:
        return self.gap_step_d * len(self.gap_steps)


P = Params()
