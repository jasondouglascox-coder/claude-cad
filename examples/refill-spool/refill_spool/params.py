"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.

The spool's axis is Z. Both halves print outer face down: the barrel half (flange + barrel + nut thread + AMS lite
core key) and the cap (flange + threaded spigot that screws into the barrel's top)."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # the refill and the AMS (docs/measurements.md)
    bore_d: float = 55.0  # AMS lite hub
    barrel_d: float = 80.0  # the refill's cardboard core is ~82 inside
    core_d: float = 82.0
    core_od: float = 87.0  # the cardboard's outside: the key has to stop inside its wall
    coil_d: float = 171.5  # filament OD of a full 1 kg coil (6.75"): straps pass over it inside the rim
    coil_w: float = 61.0
    coil_side_clear: float = 0.5  # each side, between the coil and a flange
    inside_w: float = 62.0  # flange to flange, where the coil sits
    ams_max_w: float = 68.0  # AMS lite: spools 40-68 mm wide
    rim_d: float = 200.0
    # flanges: spokes and a rim instead of a solid disc
    flange_t: float = 2.8  # 62 between flanges + 2 x 2.8 = 67.6, inside the AMS lite's 68
    rim_w: float = 3.0  # radial
    spokes: int = 6
    spoke_w: float = 6.0
    # barrel half
    barrel_wall: float = 1.2
    bore_wall: float = 1.2  # tube round the bore, the barrel half's full height (like the official spool)
    key_len: float = 6.0  # core key: on the barrel's outside at the flange, into a notch in the refill's core
    key_h: float = 3.0  # radial, out from the barrel
    key_w: float = 3.0
    key_angle: float = 0.0  # on a spoke, so it stands on the flange
    core_notch_clear: float = 0.5  # the core's notch round the key, as modelled (unmeasured)
    # cap
    spigot_wall: float = 1.6
    # thread: barrel top is the nut, cap spigot the bolt
    pitch: float = 4.0
    thread_depth: float = 1.2
    thread_crest: float = 0.5
    thread_len: float = 12.0  # thread band; the ridges run within it (parts.engaged)
    thread_clear: float = 0.3  # radial
    min_turns: float = 1.5  # engaged, screwed home
    min_play: float = 0.25  # axial, each flank: printed threads need room
    thread_flank: float = 40.0  # degrees off the axis
    # straps: zip ties under the core (in tracks on the barrel), out through the flange, over the coil
    straps: int = 3
    strap_w: float = 7.0  # track width: a groove in the barrel's outside, a tunnel once the core is over it
    strap_t: float = 1.2  # thickest strap the track must pass (zip ties up to ~6 x 1.2 mm)
    track_wall: float = 0.8  # barrel wall left behind the track
    filament: int = 3  # AMS slot: the user's PLA
    max_grams: float = 85.0  # both halves, as Bambu Studio slices them (the user's solid printed ones are ~220)
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so every top prints whole."""
        for name in ("flange_t",):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        for name in ("inside_w", "thread_len", "key_len"):  # stacked on the flange
            object.__setattr__(self, name, self.printer.layers(getattr(self, name)))
        if self.spokes % self.straps:
            raise ValueError(f"straps={self.straps} must divide spokes={self.spokes} (a strap between every "
                             f"spokes/straps spokes)")

    @property
    def width(self) -> float:
        """Overall, outer face to outer face (ams_max_w)."""
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
    def track_floor(self) -> float:
        """Radius of each strap track's floor (flat, at its middle)."""
        return self.nut_root + self.track_wall

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
