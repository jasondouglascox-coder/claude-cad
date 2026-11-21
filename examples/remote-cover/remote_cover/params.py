"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The HEXBUG remote's battery pocket, measured off photos (docs/measurements.md): a rounded rectangle with an ear
recess on top over the brass screw insert, and slots under its bottom edge for the cover's tabs. The cover fills the
pocket less a clearance on every side; with no screw, a round plug under the ear sits in the indent, which is the
recess's round end, concentric with the insert, and the snug outline holds it. The tongue's length is a guess (the
second print's was about 0.5 too long), so the plate prints a ladder of tongue lengths.

Model frame: the pocket's outline at Z = 0, X across the remote, the ear toward +Y, seen from the INSIDE face (the
print's top). Seen from outside the remote, left and right swap."""
from dataclasses import dataclass, replace

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    pocket_w: float = 26.1  # across the remote
    pocket_h: float = 16.2  # bottom edge to top edge, ear recess not included
    pocket_r: float = 1.0  # the pocket's corners
    ear_w: float = 6.2  # the ear recess, centered on the top edge
    ear_tip: float = 6.4  # how far the recess's round end reaches above the top edge: 6.9 printed ~0.5 too long
    ear_tips: tuple = (6.2, 6.4, 6.6)  # one cover each on the plate; keep the one that drops in
    shoulder_r: float = 1.0  # where the ear recess meets the top edge
    clearance: float = 0.2  # gap on every side: of 0.1 / 0.2 / 0.3, the 0.2 cover fit
    t: float = 1.6  # plate thickness: the first print sat about flush
    hole_d: float = 1.6  # through the ear and plug: clears an M1.4 screw if one turns up
    tab_dx: tuple = (-6.8, 4.8)  # tab centers from the pocket's center (inside view; outside: 4.8 left, 6.8 right)
    tab_w: float = 2.0  # along the bottom edge (slots about 2.9)
    tab_out: float = 1.0  # past the cover's bottom edge, under the pocket's lip
    tab_t: float = 0.75  # flush with the inside face; snapped to layers
    plug_d: float = 4.8  # the indent (the recess's round end) is about 5, centered on the insert
    plug_h: float = 0.8  # how far the plug stands off the inside face (indent depth not measured)
    plug_chamfer: float = 0.2  # lead-in round the plug's top edge
    mark_size: float = 3.2  # the tongue length engraved on the inside face, in tenths: "64" = 6.4 mm
    mark_depth: float = 0.2
    # the AMS lite (type, color) per slot: the cover prints in gray PETG, slot 1 as for the railroad
    filaments: tuple = (("PETG", "#8A8A8A"), ("PETG", "#5A3A1E"), ("PLA", "#000000"), ("PLA", "#6F4A2A"))
    filament_gray: int = 1  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so every top prints whole."""
        for name in ("t", "tab_t", "plug_h", "mark_depth"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        if self.tab_t >= self.t:
            raise ValueError(f"tab_t {self.tab_t} must be thinner than the plate t {self.t}")
        if self.plug_d > self.ear_w - 2 * self.clearance:
            raise ValueError(f"plug_d {self.plug_d} won't fit under a {self.ear_w} ear")
        if self.ear_tip - self.ear_w / 2 < self.shoulder_r:
            raise ValueError(f"ear_tip {self.ear_tip} is too short for a round end on a {self.ear_w} ear")
        for dx in self.tab_dx:
            if abs(dx) + self.tab_w / 2 > self.pocket_w / 2 - self.pocket_r:
                raise ValueError(f"tab at {dx} runs into the pocket's corner")

    @property
    def y0(self) -> float:
        """The pocket's bottom edge: the tabs stick out below it."""
        return self.tab_out

    @property
    def top(self) -> float:
        return self.y0 + self.pocket_h

    @property
    def cx(self) -> float:
        return self.pocket_w / 2

    @property
    def hole_up(self) -> float:
        """The insert (and the plug, and the hole) at the center of the recess's round end."""
        return self.ear_tip - self.ear_w / 2

    @property
    def hole_y(self) -> float:
        return self.top + self.hole_up

    def ladder(self) -> list["Params"]:
        """These params once per tongue length in ear_tips."""
        return [replace(self, ear_tip=e) for e in self.ear_tips]

    def tab_xs(self) -> list[tuple[float, float]]:
        """(x0, x1) of each tab along the bottom edge, left to right in the model."""
        return sorted((self.cx + dx - self.tab_w / 2, self.cx + dx + self.tab_w / 2) for dx in self.tab_dx)


P = Params()
