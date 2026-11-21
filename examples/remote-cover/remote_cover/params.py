"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The HEXBUG remote's battery pocket, measured off photos (docs/measurements.md): a rounded rectangle with an ear
recess on top over the brass screw insert, and slots under its bottom edge for the cover's tabs. The cover fills the
pocket less a clearance on every side; with no screw, a round plug under the ear sits in the indent round the insert
and the snug outline holds it. The clearance is a guess (photo measurements), so the plate prints a ladder of covers.

Model frame: the pocket's outline at Z = 0, X across the remote, the ear toward +Y, seen from the INSIDE face (the
print's top). Seen from outside the remote, left and right swap."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    pocket_w: float = 26.1  # across the remote
    pocket_h: float = 16.2  # bottom edge to top edge, ear recess not included
    pocket_r: float = 1.0  # the pocket's corners
    ear_w: float = 6.2  # the ear recess, centered on the top edge
    ear_tip: float = 6.9  # how far the recess's round end reaches above the top edge
    shoulder_r: float = 1.0  # where the ear recess meets the top edge
    hole_up: float = 2.6  # the brass insert's center above the top edge, centered across
    clearances: tuple = (0.1, 0.2, 0.3)  # gap on every side, one cover each; keep the snug one
    t: float = 1.6  # plate thickness: the first print sat about flush
    hole_d: float = 1.6  # through the ear and plug: clears an M1.4 screw if one turns up
    tab_dx: tuple = (-6.8, 4.8)  # tab centers from the pocket's center (inside view; outside: 4.8 left, 6.8 right)
    tab_w: float = 2.0  # along the bottom edge (slots about 2.9)
    tab_out: float = 1.0  # past the cover's bottom edge, under the pocket's lip
    tab_t: float = 0.75  # flush with the inside face; snapped to layers
    plug_d: float = 4.6  # the indent is about 5: room for the photo's error in where it is
    plug_h: float = 0.8  # how far the plug stands off the inside face (indent depth not measured)
    plug_chamfer: float = 0.2  # lead-in round the plug's top edge
    mark_size: float = 3.2  # the clearance engraved on the inside face, in tenths: "2" = 0.2 mm
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
        if self.plug_d > self.ear_w - 2 * max(self.clearances):
            raise ValueError(f"plug_d {self.plug_d} won't fit under a {self.ear_w} ear")
        if self.hole_up + self.plug_d / 2 > self.ear_tip:
            raise ValueError(f"plug_d {self.plug_d} at hole_up {self.hole_up} runs past the ear's tip")
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
    def hole_y(self) -> float:
        return self.top + self.hole_up

    def tab_xs(self) -> list[tuple[float, float]]:
        """(x0, x1) of each tab along the bottom edge, left to right in the model."""
        return sorted((self.cx + dx - self.tab_w / 2, self.cx + dx + self.tab_w / 2) for dx in self.tab_dx)


P = Params()
