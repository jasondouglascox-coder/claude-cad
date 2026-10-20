"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The spool's axis is Z. Both halves print outer face down: the barrel half (flange + barrel + nut thread + AMS lite
notch) and the cap (flange + threaded spigot that screws into the barrel's top)."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # the refill and the AMS (docs/measurements.md)
    bore_d: float = 55.0  # AMS lite hub
    barrel_d: float = 80.0  # the refill's cardboard core is ~82 inside
    core_d: float = 82.0
    coil_d: float = 190.0  # filament OD of a full 1 kg coil: straps pass over it inside the rim
    inside_w: float = 59.0  # flange to flange, where the coil sits
    rim_d: float = 200.0
    # flanges: spokes and a rim instead of a solid disc
    flange_t: float = 3.0
    rim_w: float = 3.0  # radial
    spokes: int = 6
    spoke_w: float = 6.0
    # barrel half
    barrel_wall: float = 1.2
    bore_wall: float = 1.2  # tube round the bore, the barrel half's full height (like the official spool)
    hub_wall: float = 4.5  # bore ring around the AMS lite hub, thick enough for the notch
    hub_h: float = 7.2
    notch_depth: float = 6.0  # AMS lite drive notch: in from the outer face along the bore
    notch_h: float = 3.0  # radial, into the bore wall
    notch_w: float = 3.0
    # cap
    cap_hub_wall: float = 2.5
    spigot_wall: float = 1.6
    lip_h: float = 2.4  # ring on the cap flange round the barrel's top: holds the slotted barrel's strips in
    lip_t: float = 0.8
    lip_clear: float = 0.2  # radial, outside the barrel
    lip_chamfer: float = 0.6  # lead-in on the lip's inner tip
    # thread: barrel top is the nut, cap spigot the bolt
    pitch: float = 4.0
    thread_depth: float = 1.2
    thread_crest: float = 0.5
    thread_len: float = 12.0  # thread band; the ridges run within it (parts.engaged)
    thread_clear: float = 0.3  # radial
    min_turns: float = 1.5  # engaged, screwed home
    min_play: float = 0.25  # axial, each flank: printed threads need room
    thread_flank: float = 40.0  # degrees off the axis
    # straps: zip ties under the core (in the barrel slots), out through the flanges, over the coil
    straps: int = 3
    strap_w: float = 10.0  # slot width in the barrel
    strap_t: float = 1.5  # thickest strap the path must pass
    filament: int = 1  # AMS slot
    max_grams: float = 75.0  # both halves, as Bambu Studio slices them (the user's solid printed ones are ~220)
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so every top prints whole."""
        for name in ("flange_t", "hub_h", "notch_depth", "lip_h"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        for name in ("inside_w", "thread_len"):  # stacked on the flange
            object.__setattr__(self, name, self.printer.layers(getattr(self, name)))
        if self.spokes % self.straps:
            raise ValueError(f"straps={self.straps} must divide spokes={self.spokes} (a strap between every "
                             f"spokes/straps spokes)")

    @property
    def width(self) -> float:
        """Overall, outer face to outer face (AMS takes about 67)."""
        return 2 * self.flange_t + self.inside_w

    @property
    def barrel_top(self) -> float:
        return self.flange_t + self.inside_w

    @property
    def nut_root(self) -> float:
        """Inside radius of the barrel wall: the nut's ridge stands on it."""
        return self.barrel_d / 2 - self.barrel_wall

    @property
    def bolt_root(self) -> float:
        """Outside radius of the cap's spigot wall: its crest sits thread_clear inside the nut's root."""
        return self.nut_root - self.thread_clear - self.thread_depth

    @property
    def rim_in(self) -> float:
        return self.rim_d / 2 - self.rim_w

    def spoke_angles(self) -> list[float]:
        return [360 * k / self.spokes for k in range(self.spokes)]

    def strap_angles(self) -> list[float]:
        """Midway between spokes, evenly spread."""
        step = self.spokes // self.straps
        return [360 * (k * step + 0.5) / self.spokes for k in range(self.straps)]


P = Params()
