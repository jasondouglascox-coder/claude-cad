"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The HEXBUG remote's battery cover, as measured off the good one (docs/measurements.md): a 25 x 15 plate with a
round-ended screw ear centered on its top edge and two small tabs on the bottom edge that hook under the pocket's
lip. No screw: a round plug under the ear presses into the circular indent round the remote's brass screw insert.
The plug's size is a guess (~5 mm), so the plate prints a ladder of covers, one per plug size."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    w: float = 25.0  # cover width, across the remote
    h: float = 15.0  # cover length, bottom edge to where the ear starts
    fit: float = 0.05  # each outside edge comes in this much: printed outlines grow a little
    corner_r: float = 0.5
    t: float = 1.6  # plate thickness: a guess, the good cover wasn't measured
    ear_w: float = 5.5  # screw ear: width, and how far it sticks out past the top edge (round end)
    ear_len: float = 5.5
    shoulder_r: float = 0.8  # where the ear meets the top edge, like the original's
    hole_d: float = 1.6  # through the ear and plug: clears an M1.4 screw if one turns up
    tab_in: float = 6.0  # each tab's outer edge from its side of the cover
    tab_w: float = 2.0  # along the bottom edge
    tab_out: float = 1.0  # past the bottom edge
    tab_t: float = 0.75  # flush with the inside face; snapped to layers
    plug_ds: tuple = (4.8, 4.9, 5.0, 5.1, 5.2)  # one cover per plug size; keep the one that presses in snug
    plug_h: float = 0.8  # how far the plug stands off the inside face (indent depth not measured)
    plug_chamfer: float = 0.2  # lead-in round the plug's top edge
    mark_size: float = 3.2  # plug size engraved on the inside face: "48" = 4.8 mm
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
        if max(self.plug_ds) > self.ear_w:
            raise ValueError(f"plug_ds up to {max(self.plug_ds)} won't fit under a {self.ear_w} ear")
        if self.tab_in + self.tab_w > self.w / 2:
            raise ValueError(f"tab_in {self.tab_in} + tab_w {self.tab_w} runs past the cover's middle")

    @property
    def y0(self) -> float:
        """The cover's bottom edge: the tabs stick out below it, down to Y = 0."""
        return self.tab_out

    @property
    def hole_x(self) -> float:
        return self.w / 2

    @property
    def hole_y(self) -> float:
        """Center of the ear's round end, where the screw hole and plug are."""
        return self.y0 + self.h + self.ear_len - self.ear_w / 2

    @property
    def length(self) -> float:
        """Overall, tab tips to ear tip."""
        return self.tab_out + self.h + self.ear_len

    def tab_xs(self) -> list[tuple[float, float]]:
        """(x0, x1) of each tab along the bottom edge."""
        return [(self.tab_in, self.tab_in + self.tab_w), (self.w - self.tab_in - self.tab_w, self.w - self.tab_in)]


P = Params()
