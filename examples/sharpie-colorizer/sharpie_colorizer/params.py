"""Every dimension in one place (mm). A design change is a one-line edit here; tests derive from these.
Measured values come from docs/measurements.md (ruler, ±0.5 mm); fits come from the fit-test plate."""
from dataclasses import dataclass

from cadkit import Printer


@dataclass(frozen=True)
class Params:
    # measured: the A1's top frame bar
    bar_w: float = 40.0  # front to back (Y)
    bar_h: float = 20.0  # (Z)
    bar_r: float = 3.0  # corner radius: not measured, only used to model the bar
    # measured: Sharpie Fine Point
    marker_body_d: float = 13.0  # main body, behind the shoulder
    marker_front_d: float = 11.0  # front section the socket grips
    front_straight_l: float = 20.0  # straight part of the front section, from the shoulder
    shoulder_to_felt_long: float = 32.0  # the direct reading
    shoulder_to_felt_short: float = 28.5  # the pieces added up (20 + 2.5 round-in + 6 nose)
    nose_l: float = 6.0  # small plastic nose the felt comes out of
    nose_d: float = 6.0  # not measured: assumed
    felt_l: float = 5.0
    felt_d: float = 4.0  # at its base, tapering to a point
    filament_d: float = 1.75
    tube_od: float = 4.0  # the A1's guide tube
    # fits: the fit-test plate picks these (one-line edits after printing it)
    marker_fit_d: float = 11.0
    marker_fits: tuple = (10.6, 10.8, 11.0, 11.2, 11.4, 11.6)
    tube_fit_d: float = 4.1
    tube_fits: tuple = (4.0, 4.1, 4.2, 4.3)
    hook: float = 2.0  # how far the clip's lips reach in under the bar
    hooks: tuple = (1.5, 2.0, 2.5)
    clip_clear: float = 0.2  # per side, around the bar
    rail_clear: float = 0.1  # per side: the railroad's proven 0.2 mm slide
    # design
    tilt_deg: float = 42.0  # marker axis from vertical, felt pointing down (downstream)
    azimuths_deg: tuple = (270.0, 30.0, 150.0)  # around the channel; 270 = back, over the bar; lowest first
    stagger: float = 8.0  # height between felt tips, so each window has the opposite wall to guide a loading end
    felt_press: float = 0.3  # how far the felt point sits inside the filament surface
    grip_min: float = 12.0  # length of the straight front section in the socket (long reading)
    shoulder_gap_min: float = 3.0  # shoulder to mouth at the short reading, worn
    wear_max: float = 1.0  # felt worn and pushed in by this much; past it the nose reaches the filament
    channel_d: float = 2.4
    wall: float = 2.4
    nose_clear: float = 1.0  # all round the nose (its size is a guess)
    felt_clear: float = 0.3
    tube_depth: float = 10.0
    bed_chamfer: float = 0.4  # outlet mouth on the bed: elephant foot would close it
    clip_w: float = 20.0  # along the bar
    clip_t: float = 2.4
    rail_neck: float = 8.0
    rail_head: float = 11.0
    rail_h: float = 4.0
    floor_t: float = 1.2  # above the rail slot's peak
    tip_lift: float = 3.0  # lowest felt tip above the base
    inlet_wall: float = 0.8  # plastic between the top marker's nose bore and the inlet's cone
    pin_hole_d: float = 2.0  # lock pin: a 1.75 mm filament stub through the base into the rail
    pin_depth: float = 3.0  # how far the pin goes into the rail
    pin_proud: float = 3.0  # how far it sticks up out of the base, to pull it
    # fit-test plate
    fit_h: float = 15.0  # marker strip height: the tilted bores grip about as long as the block's
    fit_wall: float = 1.6  # around each fit-test hole
    slice_w: float = 8.0  # clip slice thickness
    mark_w: float = 1.2  # one raised bar per variant number: 1, 2, 3 ...
    mark_l: float = 4.0
    mark_gap: float = 0.8
    mark_h: float = 0.6
    filament_black: int = 3  # AMS slot
    printer: Printer = Printer()

    def __post_init__(self):
        """Heights land on the printer's layers (yours, from cadkit.settings), so tops print whole."""
        for name in ("rail_h", "floor_t", "tube_depth", "fit_h", "slice_w"):
            object.__setattr__(self, name, self.printer.snap(getattr(self, name)))
        for name in ("mark_h",):  # stacked on a height above
            object.__setattr__(self, name, self.printer.layers(getattr(self, name)))


P = Params()
